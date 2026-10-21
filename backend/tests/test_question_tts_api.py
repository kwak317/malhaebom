from __future__ import annotations

import sys
import types
import unittest
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

if "jwt" not in sys.modules:
    fake_jwt = types.ModuleType("jwt")
    fake_exceptions = types.ModuleType("jwt.exceptions")

    class InvalidTokenError(Exception):
        pass

    class PyJWKClientError(Exception):
        pass

    class PyJWKClient:
        def __init__(self, *_: object) -> None:
            pass

    fake_jwt.PyJWKClient = PyJWKClient
    fake_jwt.decode = lambda *_args, **_kwargs: {}
    fake_jwt.exceptions = fake_exceptions
    fake_exceptions.InvalidTokenError = InvalidTokenError
    fake_exceptions.PyJWKClientError = PyJWKClientError
    sys.modules["jwt"] = fake_jwt
    sys.modules["jwt.exceptions"] = fake_exceptions

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import InvalidAccessToken
from app.main import create_app
from app.services.question_tts import (
    QuestionTtsCreation,
    QuestionTtsUnavailableError,
    normalize_question,
)
from app.services.question_tts_persistence import QuestionTtsRecord
from app.services.question_tts_stream import StreamAudio, StreamComplete, StreamError, StreamStart


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        users = {"owner-token": "user-owner", "other-token": "user-other"}
        if token not in users:
            raise InvalidAccessToken()
        return users[token]


class FakeQuestionTtsService:
    def __init__(self, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.create_calls: list[str] = []
        self.read_calls: list[tuple[str, str]] = []

    def create(self, user: object, raw_question: str) -> QuestionTtsCreation:
        text = normalize_question(raw_question)
        self.create_calls.append(text)
        if self.unavailable:
            raise QuestionTtsUnavailableError()
        return QuestionTtsCreation(
            QuestionTtsRecord(
                audio_id="audio-1",
                user_id=getattr(user, "user_id"),
                audio_path="ignored",
                duration_ms=1000,
                expires_at=datetime(2026, 8, 20, tzinfo=UTC),
            ),
            text,
        )

    def read(self, user: object, audio_id: str, now: datetime) -> bytes:
        self.read_calls.append((getattr(user, "user_id"), audio_id))
        if audio_id in {"other-user", "expired"}:
            raise KeyError(audio_id)
        if self.unavailable:
            raise QuestionTtsUnavailableError()
        return b"RIFFfake-wav"


class FakeQuestionTtsStreamService:
    def __init__(self, events: list[object] | None = None, unavailable: bool = False) -> None:
        self.events_to_send = events or [
            StreamStart(text="질문입니다."),
            StreamAudio(sequence=0, pcm16=b"\x00\x00"),
            StreamComplete(
                QuestionTtsRecord(
                    audio_id="audio-1",
                    user_id="user-owner",
                    audio_path="ignored",
                    duration_ms=1,
                    expires_at=datetime(2026, 8, 20, tzinfo=UTC),
                )
            ),
        ]
        self.unavailable = unavailable
        self.calls: list[str] = []

    def ensure_ready(self) -> None:
        if self.unavailable:
            raise QuestionTtsUnavailableError()

    def events(self, user: object, raw_question: str, cancel: threading.Event):
        self.calls.append(raw_question)
        yield from self.events_to_send


class QuestionTtsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FakeQuestionTtsService()
        self.stream_service = FakeQuestionTtsStreamService()
        self.client = TestClient(
            create_app(
                service=object(),
                token_verifier=FakeVerifier(),
                question_tts_service=self.service,
                question_tts_stream_service=self.stream_service,
            )
        )

    def test_stream_returns_start_audio_complete_ndjson_with_relative_url(self) -> None:
        with self.client.stream(
            "POST",
            "/api/questions/tts/stream",
            headers={"Authorization": "Bearer owner-token"},
            json={"question": "  질문입니다.  "},
        ) as response:
            events = [json.loads(line) for line in response.iter_lines() if line]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/x-ndjson; charset=utf-8")
        self.assertEqual([event["type"] for event in events], ["start", "audio", "complete"])
        self.assertEqual(events[0]["text"], "질문입니다.")
        self.assertEqual(events[1]["sequence"], 0)
        self.assertEqual(events[-1]["audioUrl"], "/api/audio/questions/audio-1")
        self.assertEqual(self.stream_service.calls, ["질문입니다."])

    def test_invalid_or_unauthenticated_stream_never_starts_event_stream(self) -> None:
        invalid = self.client.post(
            "/api/questions/tts/stream",
            headers={"Authorization": "Bearer owner-token"},
            json={"question": "가" * 201},
        )
        unauthenticated = self.client.post(
            "/api/questions/tts/stream", json={"question": "질문입니다."}
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(self.stream_service.calls, [])

    def test_midstream_error_is_terminal_without_complete(self) -> None:
        client = TestClient(
            create_app(
                service=object(),
                token_verifier=FakeVerifier(),
                question_tts_service=self.service,
                question_tts_stream_service=FakeQuestionTtsStreamService(
                    [
                        StreamStart(text="질문입니다."),
                        StreamError("TTS_GENERATION_FAILED", "질문 음성을 만들지 못했습니다. 다시 시도해 주세요."),
                    ]
                ),
            )
        )

        response = client.post(
            "/api/questions/tts/stream",
            headers={"Authorization": "Bearer owner-token"},
            json={"question": "질문입니다."},
        )
        events = [json.loads(line) for line in response.iter_lines() if line]

        self.assertEqual([event["type"] for event in events], ["start", "error"])
        self.assertNotIn("audioUrl", events[-1])

    def test_unavailable_stream_is_sanitized_503_before_start(self) -> None:
        client = TestClient(
            create_app(
                service=object(),
                token_verifier=FakeVerifier(),
                question_tts_service=self.service,
                question_tts_stream_service=FakeQuestionTtsStreamService(unavailable=True),
            )
        )

        response = client.post(
            "/api/questions/tts/stream",
            headers={"Authorization": "Bearer owner-token"},
            json={"question": "질문입니다."},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "질문 음성을 만들지 못했습니다. 다시 시도해 주세요.")

    def test_authenticated_create_returns_relative_url_normalized_text_duration_and_expiry(self) -> None:
        response = self.client.post(
            "/api/questions/tts",
            headers={"Authorization": "Bearer owner-token"},
            json={"question": "  협업 경험을 말해 주세요.  "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["audioUrl"], "/api/audio/questions/audio-1")
        self.assertEqual(response.json()["text"], "협업 경험을 말해 주세요.")
        self.assertEqual(response.json()["durationMs"], 1000)
        self.assertIn("expiresAt", response.json())

    def test_invalid_question_is_400_and_never_calls_tts(self) -> None:
        response = self.client.post(
            "/api/questions/tts",
            headers={"Authorization": "Bearer owner-token"},
            json={"question": "가" * 201},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "질문은 공백 제외 1자 이상 200자 이하로 입력해 주세요.")
        self.assertEqual(self.service.create_calls, [])

    def test_missing_token_is_401(self) -> None:
        response = self.client.post("/api/questions/tts", json={"question": "질문입니다."})

        self.assertEqual(response.status_code, 401)

    def test_model_failure_is_sanitized_503(self) -> None:
        client = TestClient(
            create_app(
                service=object(),
                token_verifier=FakeVerifier(),
                question_tts_service=FakeQuestionTtsService(unavailable=True),
            )
        )

        response = client.post(
            "/api/questions/tts",
            headers={"Authorization": "Bearer owner-token"},
            json={"question": "질문입니다."},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "질문 음성을 만들지 못했습니다. 다시 시도해 주세요.")

    def test_owner_can_download_wav_but_other_user_or_expired_audio_is_404(self) -> None:
        owner = self.client.get("/api/audio/questions/audio-1", headers={"Authorization": "Bearer owner-token"})
        other_user = self.client.get("/api/audio/questions/other-user", headers={"Authorization": "Bearer other-token"})
        expired = self.client.get("/api/audio/questions/expired", headers={"Authorization": "Bearer owner-token"})

        self.assertEqual(owner.status_code, 200)
        self.assertEqual(owner.headers["content-type"], "audio/wav")
        self.assertEqual(owner.content, b"RIFFfake-wav")
        self.assertEqual(other_user.status_code, 404)
        self.assertEqual(expired.status_code, 404)


if __name__ == "__main__":
    unittest.main()
