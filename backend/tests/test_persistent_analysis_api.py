from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import InvalidAccessToken
from app.main import create_app
from app.schemas.delivery import SpeechSegment
from app.schemas.stt import FillerAnalysis, SttResult
from app.services.delivery_analysis import DeliveryAnalyzer
from app.services.persistent_analysis_jobs import PersistentAnalysisJobService
from app.services.supabase_persistence import SupabasePersistenceError


def wav_bytes(seconds: float = 6.0) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as file:
        path = Path(file.name)
    try:
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
            audio.writeframes(b"\x00\x00" * int(16000 * seconds))
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        users = {"owner-token": "owner", "other-token": "other"}
        if token not in users:
            raise InvalidAccessToken()
        return users[token]


class FakeTranscriber:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_path, source_id, *, initial_prompt=None):
        self.calls.append((source_id, initial_prompt))
        return SttResult(source_id, "test", "cpu", "int8", "ko", 1.0, 6.0, 0.1, 0.02, "전사", FillerAnalysis({"음": 0}, 0, {"음": []}), [], [])


class FakeVad:
    def detect(self, audio_path):
        return [SpeechSegment(0.0, 3.0)]


class FakeQuestionFeedbackGenerator:
    def __init__(self):
        self.generated_questions = []

    def get_preset(self, question_id):
        return {"question": "지원한 이유를 말씀해주세요."} if question_id == "2" else None

    def generate(self, question):
        self.generated_questions.append(question)
        return {
            "question_id": "custom",
            "question": question,
            "required_concepts": [
                {"id": "problem_context", "description": "문제 상황"},
                {"id": "own_action", "description": "본인의 해결 행동"},
                {"id": "result_verification", "description": "결과 확인"},
            ],
            "recommended_keywords": [],
        }

    def evaluate(self, transcript, rubric):
        return {"feedback": "지원 직무와 연결되는 경험을 덧붙여 보세요."}

    def generate_example(self, question, transcript, content_feedback):
        return f"{transcript} 지원 직무와 연결되는 경험을 덧붙이겠습니다."


class FakeRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}
        self.practice_sessions: dict[str, dict[str, object]] = {}
        self.stt_hint_contexts: dict[str, list[str]] = {}
        self.history_delete_error = False

    def create_job(self, user, job_id, metadata, content, filename, content_type):
        row = {"id": job_id, "user_id": user.user_id, "audio_path": f"{user.user_id}/{job_id}/original.wav", "result": None, "delivery": None, "error": None, **metadata}
        self.rows[job_id] = row
        return row

    def get_job(self, user, job_id):
        row = self.rows.get(job_id)
        if row is None or row["user_id"] != user.user_id:
            raise KeyError(job_id)
        return row

    def get_attempt_one(self, user, practice_session_id):
        for row in self.rows.values():
            if row["user_id"] == user.user_id and row["practice_session_id"] == practice_session_id and row["attempt_no"] == 1:
                return row
        raise KeyError(practice_session_id)

    def get_practice_session(self, user, practice_session_id):
        row = self.practice_sessions.get(practice_session_id)
        if row is None or row["user_id"] != user.user_id:
            raise KeyError(practice_session_id)
        return row

    def get_stt_hint_context(self, user, practice_session_id):
        row = self.practice_sessions.get(practice_session_id)
        if row is None or row["user_id"] != user.user_id:
            raise KeyError(practice_session_id)
        return self.stt_hint_contexts.get(practice_session_id, [])

    def mark_processing(self, user, job_id):
        self.get_job(user, job_id)["status"] = "processing"

    def mark_completed(self, user, job_id, result, delivery):
        row = self.get_job(user, job_id); row.update(status="completed", result=result, delivery=delivery, completed_at="2026-08-24T10:00:00+00:00")

    def mark_failed(self, user, job_id, code, message):
        self.get_job(user, job_id).update(status="failed", error={"code": code, "message": message})

    def delete_job(self, user, job_id):
        self.get_job(user, job_id); del self.rows[job_id]

    def list_completed_jobs(self, user):
        return [row for row in self.rows.values() if row["user_id"] == user.user_id and row.get("status") == "completed"]

    def get_completed_session_jobs(self, user, practice_session_id):
        rows = [row for row in self.list_completed_jobs(user) if row["practice_session_id"] == practice_session_id]
        if not rows:
            raise KeyError(practice_session_id)
        return rows

    def get_session_jobs(self, user, practice_session_id):
        rows = [row for row in self.rows.values() if row["user_id"] == user.user_id and row["practice_session_id"] == practice_session_id]
        if not rows:
            raise KeyError(practice_session_id)
        return rows

    def delete_session_jobs(self, user, practice_session_id, rows):
        if self.history_delete_error:
            raise SupabasePersistenceError("PERSISTENCE_UNAVAILABLE", "저장소에 연결하지 못했습니다.")
        for row in rows:
            del self.rows[row["id"]]


class PersistentAnalysisApiTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.repository = FakeRepository()
        self.transcriber = FakeTranscriber()
        service = PersistentAnalysisJobService(self.repository, self.transcriber, self.directory.name, FakeVad(), DeliveryAnalyzer())
        self.client = TestClient(create_app(service, token_verifier=FakeVerifier()))

    def tearDown(self):
        self.directory.cleanup()

    def post(self, data):
        return self.client.post("/analysis-jobs", headers={"Authorization": "Bearer owner-token"}, data=data, files={"audio": ("answer.wav", wav_bytes(), "audio/wav")})

    def test_preset_requires_question_id_before_job_creation(self):
        response = self.post({"source_id": "one", "question_type": "preset", "attempt_no": "1"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_QUESTION")
        self.assertEqual(self.repository.rows, {})

    def test_preset_attempts_share_session_and_other_user_cannot_read_or_delete(self):
        first = self.post({"source_id": "one", "question_type": "preset", "question_id": "q-1", "attempt_no": "1"})
        self.assertEqual(first.status_code, 202)
        session_id = first.json()["practice_session_id"]
        second = self.post({"source_id": "two", "question_type": "preset", "question_id": "q-1", "attempt_no": "2", "practice_session_id": session_id})
        self.assertEqual(second.status_code, 202)
        job_id = first.json()["job_id"]
        headers = {"Authorization": "Bearer other-token"}
        self.assertEqual(self.client.get(f"/analysis-jobs/{job_id}", headers=headers).status_code, 404)
        self.assertEqual(self.client.delete(f"/analysis-jobs/{job_id}", headers=headers).status_code, 404)
        self.assertEqual(self.client.delete(f"/analysis-jobs/{job_id}", headers={"Authorization": "Bearer owner-token"}).status_code, 204)
        self.assertNotIn(job_id, self.repository.rows)

    def test_first_attempt_uses_the_job_and_question_session_created_during_setup(self):
        session_id = "30000000-0000-4000-8000-000000000001"
        self.repository.practice_sessions[session_id] = {
            "user_id": "owner",
            "question_type": "preset",
            "question_id": "preset-04",
            "custom_question_text": None,
        }

        response = self.post({
            "source_id": "one",
            "question_type": "preset",
            "question_id": "preset-04",
            "attempt_no": "1",
            "practice_session_id": session_id,
        })

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["practice_session_id"], session_id)

    def test_practice_session_context_is_forwarded_as_stt_initial_prompt(self):
        session_id = "30000000-0000-4000-8000-000000000002"
        self.repository.practice_sessions[session_id] = {
            "user_id": "owner",
            "question_type": "preset",
            "question_id": "preset-04",
            "custom_question_text": None,
        }
        self.repository.stt_hint_contexts[session_id] = [
            "Python FastAPI Docker 백엔드 엔지니어"
        ]

        response = self.post({
            "source_id": "one",
            "question_type": "preset",
            "question_id": "preset-04",
            "attempt_no": "1",
            "practice_session_id": session_id,
        })

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            self.transcriber.calls[-1][1],
            "기술 면접 답변입니다. 다음 기술 용어가 등장할 수 있습니다: Python, FastAPI, Docker.",
        )

    def test_second_attempt_requires_first_attempt_session(self):
        response = self.post({"source_id": "two", "question_type": "preset", "question_id": "q-1", "attempt_no": "2"})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_QUESTION")
        self.assertEqual(self.repository.rows, {})

    def test_second_attempt_must_use_the_same_question(self):
        first = self.post({"source_id": "one", "question_type": "preset", "question_id": "q-1", "attempt_no": "1"})
        session_id = first.json()["practice_session_id"]

        response = self.post({"source_id": "two", "question_type": "preset", "question_id": "q-2", "attempt_no": "2", "practice_session_id": session_id})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_QUESTION")
        self.assertEqual(len(self.repository.rows), 1)

    def test_custom_question_rejects_blank_or_overlong_text(self):
        for text in ("   ", "가" * 201):
            response = self.post({"source_id": "one", "question_type": "custom", "custom_question_text": text, "attempt_no": "1"})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["detail"]["code"], "INVALID_QUESTION")

    def test_completed_job_defers_content_coaching_until_transcript_confirmation(self):
        service = PersistentAnalysisJobService(
            self.repository,
            FakeTranscriber(),
            self.directory.name,
            FakeVad(),
            DeliveryAnalyzer(),
            FakeQuestionFeedbackGenerator(),
        )
        client = TestClient(create_app(service, token_verifier=FakeVerifier()))
        response = client.post(
            "/analysis-jobs",
            headers={"Authorization": "Bearer owner-token"},
            data={"source_id": "one", "question_type": "preset", "question_id": "2", "attempt_no": "1"},
            files={"audio": ("answer.wav", wav_bytes(), "audio/wav")},
        )
        self.assertEqual(response.status_code, 202)
        job = client.get(f"/analysis-jobs/{response.json()['job_id']}", headers={"Authorization": "Bearer owner-token"}).json()
        self.assertNotIn("content_feedback", job["result"])
        self.assertNotIn("improved_answer", job["result"])

    def test_question_feedback_waits_for_confirmed_transcript(self):
        generator = FakeQuestionFeedbackGenerator()
        service = PersistentAnalysisJobService(
            self.repository,
            FakeTranscriber(),
            self.directory.name,
            FakeVad(),
            DeliveryAnalyzer(),
            generator,
        )
        client = TestClient(create_app(service, token_verifier=FakeVerifier()))
        request = {
            "source_id": "one",
            "question_type": "custom",
            "custom_question_text": "문제를 해결한 경험을 말해 주세요.",
            "attempt_no": "1",
        }
        first = client.post(
            "/analysis-jobs",
            headers={"Authorization": "Bearer owner-token"},
            data=request,
            files={"audio": ("answer.wav", wav_bytes(), "audio/wav")},
        )
        self.assertEqual(first.status_code, 202)
        second = client.post(
            "/analysis-jobs",
            headers={"Authorization": "Bearer owner-token"},
            data={**request, "source_id": "two", "attempt_no": "2", "practice_session_id": first.json()["practice_session_id"]},
            files={"audio": ("answer.wav", wav_bytes(), "audio/wav")},
        )
        self.assertEqual(second.status_code, 202)

        first_result = self.repository.rows[first.json()["job_id"]]["result"]
        second_result = self.repository.rows[second.json()["job_id"]]["result"]
        self.assertEqual(generator.generated_questions, [])
        self.assertNotIn("content_feedback", first_result)
        self.assertNotIn("content_feedback", second_result)

    def test_history_list_returns_only_completed_owner_records(self):
        self.repository.rows["history-job"] = history_row("history-job", "owner", "session-owned")
        self.repository.rows["other-job"] = history_row("other-job", "other", "session-other")

        response = self.client.get("/practice-records", headers={"Authorization": "Bearer owner-token"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([record["practice_session_id"] for record in response.json()["records"]], ["session-owned"])

    def test_history_detail_and_delete_hide_other_users_session(self):
        self.repository.rows["history-job"] = history_row("history-job", "owner", "session-owned")

        other_headers = {"Authorization": "Bearer other-token"}
        self.assertEqual(self.client.get("/practice-records/session-owned", headers=other_headers).status_code, 404)
        self.assertEqual(self.client.delete("/practice-records/session-owned", headers=other_headers).status_code, 404)

        owner_headers = {"Authorization": "Bearer owner-token"}
        self.assertEqual(self.client.delete("/practice-records/session-owned", headers=owner_headers).status_code, 204)
        self.assertNotIn("history-job", self.repository.rows)

    def test_history_delete_returns_503_when_storage_cleanup_cannot_finish(self):
        self.repository.rows["history-job"] = history_row("history-job", "owner", "session-owned")
        self.repository.history_delete_error = True

        response = self.client.delete("/practice-records/session-owned", headers={"Authorization": "Bearer owner-token"})

        self.assertEqual(response.status_code, 503)
        self.assertIn("history-job", self.repository.rows)

    def test_history_delete_all_removes_only_current_users_completed_sessions(self):
        self.repository.rows["owner-job"] = history_row("owner-job", "owner", "session-owner")
        self.repository.rows["other-job"] = history_row("other-job", "other", "session-other")

        response = self.client.delete("/practice-records", headers={"Authorization": "Bearer owner-token"})

        self.assertEqual(response.status_code, 204)
        self.assertNotIn("owner-job", self.repository.rows)
        self.assertIn("other-job", self.repository.rows)


def history_row(job_id, user_id, practice_session_id):
    return {
        "id": job_id,
        "user_id": user_id,
        "practice_session_id": practice_session_id,
        "question_type": "preset",
        "question_id": "preset-01",
        "custom_question_text": None,
        "attempt_no": 1,
        "audio_path": f"{user_id}/{job_id}/original.wav",
        "status": "completed",
        "completed_at": "2026-08-24T10:00:00+00:00",
        "result": {"text": "전사"},
        "delivery": {"metrics": {"cpm": 330, "long_silences": [], "repetitions": []}, "feedback": []},
    }
