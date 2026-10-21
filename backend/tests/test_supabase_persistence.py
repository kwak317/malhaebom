from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import AuthenticatedUser
from app.core.supabase_settings import SupabaseSettings
from app.services.supabase_persistence import SupabaseAnalysisRepository, SupabasePersistenceError


class FakeResponse:
    def __init__(self, status_code: int, body: object = None) -> None:
        self.status_code = status_code
        self.body = [] if body is None else body

    def json(self):
        return self.body


class FakeHttpClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


SETTINGS = SupabaseSettings("https://project.supabase.co", "publishable-key")
USER = AuthenticatedUser("user-1", "user-access-token")
METADATA = {"source_id": "source-1", "practice_session_id": "session-1", "question_type": "preset", "question_id": "q-1", "custom_question_text": None, "attempt_no": 1, "status": "queued"}


class SupabaseAnalysisRepositoryTest(unittest.TestCase):
    def test_uploads_with_user_jwt_and_creates_row(self):
        http = FakeHttpClient([FakeResponse(200), FakeResponse(201, [{"id": "job-1", **METADATA}])])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        row = repository.create_job(USER, "job-1", METADATA, b"audio", "answer.wav", "audio/wav")

        upload = http.requests[0]
        self.assertEqual(upload["headers"]["Authorization"], "Bearer user-access-token")
        self.assertEqual(upload["headers"]["apikey"], "publishable-key")
        self.assertTrue(upload["url"].endswith("/storage/v1/object/analysis-audio/user-1/job-1/original.wav"))
        self.assertEqual(http.requests[1]["json"]["user_id"], "user-1")
        self.assertEqual(row["id"], "job-1")

    def test_db_insert_failure_removes_uploaded_object(self):
        http = FakeHttpClient([FakeResponse(200), FakeResponse(500), FakeResponse(200)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        with self.assertRaises(SupabasePersistenceError):
            repository.create_job(USER, "job-1", METADATA, b"audio", "answer.wav", "audio/wav")

        self.assertEqual([request["method"] for request in http.requests], ["POST", "POST", "DELETE"])
        self.assertTrue(http.requests[2]["url"].endswith("/storage/v1/object/analysis-audio"))

    def test_storage_failure_does_not_create_row(self):
        http = FakeHttpClient([FakeResponse(403)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        with self.assertRaisesRegex(SupabasePersistenceError, "Storage RLS 정책.*HTTP 403"):
            repository.create_job(USER, "job-1", METADATA, b"audio", "answer.wav", "audio/wav")

        self.assertEqual(len(http.requests), 1)

    def test_not_found_error_identifies_missing_storage_configuration(self):
        http = FakeHttpClient([FakeResponse(404)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        with self.assertRaisesRegex(SupabasePersistenceError, "버킷 또는 테이블.*HTTP 404"):
            repository.create_job(USER, "job-1", METADATA, b"audio", "answer.wav", "audio/wav")

    def test_delete_removes_storage_before_database_row(self):
        row = {"id": "job-1", "audio_path": "user-1/job-1/original.wav"}
        http = FakeHttpClient([FakeResponse(200, [row]), FakeResponse(200), FakeResponse(204)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        repository.delete_job(USER, "job-1")

        self.assertEqual([request["method"] for request in http.requests], ["GET", "DELETE", "DELETE"])
        self.assertIn("/storage/v1/object/analysis-audio", http.requests[1]["url"])
        self.assertIn("/rest/v1/analysis_jobs?id=eq.job-1", http.requests[2]["url"])

    def test_owner_scoped_query_returns_key_error_for_rls_empty_response(self):
        http = FakeHttpClient([FakeResponse(200, [])])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        with self.assertRaises(KeyError):
            repository.get_job(USER, "another-users-job")

        self.assertEqual(http.requests[0]["headers"]["Authorization"], "Bearer user-access-token")

    def test_attempt_one_query_requires_completed_unexpired_owner_record(self):
        rows = [{"id": "job-1", "attempt_no": 1, "status": "completed"}]
        http = FakeHttpClient([FakeResponse(200, rows)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        self.assertEqual(repository.get_attempt_one(USER, "session-1"), rows[0])

        request = http.requests[0]
        self.assertEqual(request["headers"]["Authorization"], "Bearer user-access-token")
        self.assertIn("practice_session_id=eq.session-1", request["url"])
        self.assertIn("attempt_no=eq.1", request["url"])
        self.assertIn("status=eq.completed", request["url"])
        self.assertIn("expires_at=gt.", request["url"])

    def test_list_completed_jobs_uses_owner_jwt_and_history_filters(self):
        http = FakeHttpClient([FakeResponse(200, [])])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        self.assertEqual(repository.list_completed_jobs(USER), [])

        request = http.requests[0]
        self.assertEqual(request["headers"]["Authorization"], "Bearer user-access-token")
        self.assertIn("status=eq.completed", request["url"])
        self.assertIn("expires_at=gt.", request["url"])
        self.assertIn("order=completed_at.desc", request["url"])
        self.assertIn("limit=100", request["url"])
        self.assertIn("answer_revisions", request["url"])
        self.assertIn("coaching_runs", request["url"])

    def test_completed_session_query_is_owner_scoped_and_attempt_ordered(self):
        rows = [{"id": "job-1", "attempt_no": 1}]
        http = FakeHttpClient([FakeResponse(200, rows)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        self.assertEqual(repository.get_completed_session_jobs(USER, "session-1"), rows)

        request = http.requests[0]
        self.assertEqual(request["headers"]["Authorization"], "Bearer user-access-token")
        self.assertIn("practice_session_id=eq.session-1", request["url"])
        self.assertIn("status=eq.completed", request["url"])
        self.assertIn("expires_at=gt.", request["url"])
        self.assertIn("order=attempt_no.asc", request["url"])
        self.assertIn("answer_revisions", request["url"])
        self.assertIn("coaching_runs", request["url"])

    def test_practice_setup_session_query_keeps_user_rls_scope(self):
        rows = [{
            "id": "session-1",
            "job_posting_id": "job-1",
            "question_type": "preset",
            "question_id": "preset-04",
            "custom_question_text": None,
        }]
        http = FakeHttpClient([FakeResponse(200, rows)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        self.assertEqual(repository.get_practice_session(USER, "session-1"), rows[0])

        request = http.requests[0]
        self.assertEqual(request["headers"]["Authorization"], "Bearer user-access-token")
        self.assertIn("/rest/v1/practice_sessions?id=eq.session-1", request["url"])

    def test_stt_hint_context_uses_session_posting_and_selected_requirements(self):
        http = FakeHttpClient([
            FakeResponse(200, [{
                "id": "session-1",
                "job_posting_id": "job-1",
                "question_type": "custom",
                "question_id": None,
                "custom_question_text": "Docker 경험을 설명해 주세요.",
            }]),
            FakeResponse(200, [{"title": "Python 백엔드 엔지니어"}]),
            FakeResponse(200, [
                {"job_requirements": {"requirement_text": "FastAPI와 PostgreSQL 경험"}},
                {"job_requirements": {"requirement_text": "AWS 배포 경험"}},
            ]),
        ])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        context = repository.get_stt_hint_context(USER, "session-1")

        self.assertEqual(
            context,
            [
                "Docker 경험을 설명해 주세요.",
                "Python 백엔드 엔지니어",
                "FastAPI와 PostgreSQL 경험",
                "AWS 배포 경험",
            ],
        )
        self.assertIn("select=title", http.requests[1]["url"])
        self.assertIn("practice_session_id=eq.session-1", http.requests[2]["url"])

    def test_delete_session_removes_all_storage_objects_before_one_database_delete(self):
        rows = [
            {"id": "job-1", "audio_path": "user-1/job-1/original.wav"},
            {"id": "job-2", "audio_path": "user-1/job-2/original.wav"},
        ]
        http = FakeHttpClient([FakeResponse(200), FakeResponse(200), FakeResponse(204)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        repository.delete_session_jobs(USER, "session-1", rows)

        self.assertEqual([request["method"] for request in http.requests], ["DELETE", "DELETE", "DELETE"])
        self.assertIn("/storage/v1/object/analysis-audio", http.requests[0]["url"])
        self.assertIn("/storage/v1/object/analysis-audio", http.requests[1]["url"])
        self.assertIn("practice_session_id=eq.session-1", http.requests[2]["url"])

    def test_session_storage_failure_keeps_all_database_rows_for_retry(self):
        rows = [{"id": "job-1", "audio_path": "user-1/job-1/original.wav"}]
        http = FakeHttpClient([FakeResponse(503)])
        repository = SupabaseAnalysisRepository(SETTINGS, http)

        with self.assertRaises(SupabasePersistenceError):
            repository.delete_session_jobs(USER, "session-1", rows)

        self.assertEqual(len(http.requests), 1)
        self.assertEqual(http.requests[0]["method"], "DELETE")
