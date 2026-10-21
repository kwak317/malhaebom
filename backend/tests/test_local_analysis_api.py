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

from app.main import cors_origins_from_env, create_app
from app.core.auth import InvalidAccessToken
from app.schemas.delivery import SpeechSegment
from app.schemas.stt import FillerAnalysis, SttResult
from app.services.delivery_analysis import DeliveryAnalyzer
from app.services.local_analysis_jobs import LocalAnalysisJobService


def wav_bytes(duration_seconds: float) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
        path = Path(temp.name)
    try:
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16_000)
            audio.writeframes(b"\x00\x00" * int(16_000 * duration_seconds))
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


class FakeTranscriber:
    def transcribe(self, audio_path: Path | str, source_id: str) -> SttResult:
        return SttResult(
            source_id=source_id,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            language="ko",
            language_probability=0.99,
            audio_duration_sec=6.0,
            processing_time_sec=0.2,
            rtf=0.0333,
            text="전사문",
            fillers=FillerAnalysis(counts={"음": 0, "어": 0}, total_count=0, occurrences={"음": [], "어": []}),
            segments=[],
            words=[],
        )


class FakeVadDetector:
    def detect(self, audio_path: Path) -> list[SpeechSegment]:
        return [SpeechSegment(start=0.0, end=3.0)]


def create_test_service(directory: str) -> LocalAnalysisJobService:
    return LocalAnalysisJobService(
        FakeTranscriber(),
        Path(directory),
        vad_detector=FakeVadDetector(),
        delivery_analyzer=DeliveryAnalyzer(),
    )


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        users = {"owner-token": "user-owner", "other-token": "user-other"}
        try:
            return users[token]
        except KeyError as error:
            raise InvalidAccessToken() from error


class LocalAnalysisApiTest(unittest.TestCase):
    def test_create_and_get_completed_analysis_job(self):
        with tempfile.TemporaryDirectory() as directory:
            service = create_test_service(directory)
            client = TestClient(create_app(service, token_verifier=FakeVerifier()))
            create_response = client.post(
                "/analysis-jobs",
                headers={"Authorization": "Bearer owner-token"},
                data={"source_id": "attempt-123", "question_type": "preset", "question_id": "q-1", "attempt_no": "1"},
                files={"audio": ("answer.wav", wav_bytes(6.0), "audio/wav")},
            )

            self.assertEqual(create_response.status_code, 202)
            job_id = create_response.json()["job_id"]
            get_response = client.get(
                f"/analysis-jobs/{job_id}", headers={"Authorization": "Bearer owner-token"}
            )

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["status"], "completed")
        self.assertEqual(get_response.json()["result"]["source_id"], "attempt-123")
        self.assertEqual(get_response.json()["delivery"]["metrics"]["speech_duration_sec"], 3.0)

    def test_rejects_short_audio_before_creating_job(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(create_test_service(directory), token_verifier=FakeVerifier()))
            response = client.post(
                "/analysis-jobs",
                headers={"Authorization": "Bearer owner-token"},
                data={"source_id": "attempt-123", "question_type": "preset", "question_id": "q-1", "attempt_no": "1"},
                files={"audio": ("answer.wav", wav_bytes(4.0), "audio/wav")},
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_DURATION")

    def test_returns_not_found_for_unknown_job(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(create_test_service(directory), token_verifier=FakeVerifier()))
            response = client.get("/analysis-jobs/unknown", headers={"Authorization": "Bearer owner-token"})

        self.assertEqual(response.status_code, 404)

    def test_rejects_analysis_job_creation_without_bearer_token(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(create_test_service(directory), token_verifier=FakeVerifier()))
            response = client.post(
                "/analysis-jobs",
                data={"source_id": "attempt-123", "question_type": "preset", "question_id": "q-1", "attempt_no": "1"},
                files={"audio": ("answer.wav", wav_bytes(6.0), "audio/wav")},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "UNAUTHORIZED")

    def test_rejects_analysis_job_creation_with_invalid_bearer_token(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(create_test_service(directory), token_verifier=FakeVerifier()))
            response = client.post(
                "/analysis-jobs",
                headers={"Authorization": "Bearer invalid-token"},
                data={"source_id": "attempt-123", "question_type": "preset", "question_id": "q-1", "attempt_no": "1"},
                files={"audio": ("answer.wav", wav_bytes(6.0), "audio/wav")},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "UNAUTHORIZED")

    def test_rejects_job_lookup_by_a_different_authenticated_user(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(create_test_service(directory), token_verifier=FakeVerifier()))
            create_response = client.post(
                "/analysis-jobs",
                headers={"Authorization": "Bearer owner-token"},
                data={"source_id": "attempt-123", "question_type": "preset", "question_id": "q-1", "attempt_no": "1"},
                files={"audio": ("answer.wav", wav_bytes(6.0), "audio/wav")},
            )
            job_id = create_response.json()["job_id"]
            response = client.get(
                f"/analysis-jobs/{job_id}", headers={"Authorization": "Bearer other-token"}
            )

        self.assertEqual(response.status_code, 404)

    def test_allows_only_local_frontend_cors_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(
                create_app(
                    create_test_service(directory),
                    token_verifier=FakeVerifier(),
                    allowed_origins=cors_origins_from_env({}),
                )
            )
            allowed = client.options(
                "/analysis-jobs",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "POST",
                },
            )
            compose_allowed = client.options(
                "/analysis-jobs",
                headers={
                    "Origin": "http://localhost:18080",
                    "Access-Control-Request-Method": "POST",
                },
            )
            denied = client.options(
                "/analysis-jobs",
                headers={
                    "Origin": "http://example.com",
                    "Access-Control-Request-Method": "POST",
                },
            )

        self.assertEqual(allowed.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(compose_allowed.headers.get("access-control-allow-origin"), "http://localhost:18080")
        self.assertIsNone(denied.headers.get("access-control-allow-origin"))

    def test_allows_only_injected_loopback_cors_origins(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(
                create_app(
                    create_test_service(directory),
                    token_verifier=FakeVerifier(),
                    allowed_origins=[
                        "http://localhost:5173",
                        "http://127.0.0.1:5173",
                    ],
                )
            )
            allowed = client.options(
                "/analysis-jobs",
                headers={
                    "Origin": "http://127.0.0.1:5173",
                    "Access-Control-Request-Method": "POST",
                },
            )
            denied = client.options(
                "/analysis-jobs",
                headers={
                    "Origin": "http://example.com",
                    "Access-Control-Request-Method": "POST",
                },
            )

        self.assertEqual(
            allowed.headers.get("access-control-allow-origin"),
            "http://127.0.0.1:5173",
        )
        self.assertIsNone(denied.headers.get("access-control-allow-origin"))

    def test_uses_only_configured_deployment_cors_origins(self):
        origins = cors_origins_from_env({"CORS_ALLOWED_ORIGINS": "https://app.example.com, https://staging.example.com"})
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(
                create_app(
                    create_test_service(directory),
                    token_verifier=FakeVerifier(),
                    allowed_origins=origins,
                )
            )
            allowed = client.options(
                "/analysis-jobs",
                headers={
                    "Origin": "https://app.example.com",
                    "Access-Control-Request-Method": "POST",
                },
            )
            denied = client.options(
                "/analysis-jobs",
                headers={
                    "Origin": "http://example.com",
                    "Access-Control-Request-Method": "POST",
                },
            )

        self.assertEqual(origins, ["https://app.example.com", "https://staging.example.com"])
        self.assertEqual(allowed.headers.get("access-control-allow-origin"), "https://app.example.com")
        self.assertIsNone(denied.headers.get("access-control-allow-origin"))
