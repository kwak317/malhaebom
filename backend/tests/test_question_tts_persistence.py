from __future__ import annotations

import io
import sys
import unittest
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.supabase_settings import SupabaseSettings
from app.services.question_tts_persistence import (
    SupabaseExpiredQuestionTtsRepository,
    SupabaseQuestionTtsRepository,
    QuestionTtsPersistenceError,
)


class FakeResponse:
    def __init__(self, status_code: int, body: object = None) -> None:
        self.status_code = status_code
        self.body = [] if body is None else body

    def json(self) -> object:
        return self.body


class FakeHttpClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


@dataclass(frozen=True)
class FakeGeneratedQuestionAudio:
    wav_bytes: bytes
    duration_ms: int


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    access_token: str


SETTINGS = SupabaseSettings("https://project.supabase.co", "publishable-key", "service-role-key")
USER = AuthenticatedUser("user-1", "user-access-token")
AUDIO_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
AUDIO_PATH = f"user-1/{AUDIO_ID}/question.wav"
RECORD = {
    "id": str(AUDIO_ID),
    "user_id": "user-1",
    "audio_path": AUDIO_PATH,
    "duration_ms": 1200,
    "expires_at": "2026-08-20T00:00:00Z",
}


def valid_wav() -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24_000)
        output.writeframes(b"\x00\x00" * 24_000)
    return stream.getvalue()


class SupabaseQuestionTtsRepositoryTest(unittest.TestCase):
    def test_create_uploads_private_wav_then_inserts_metadata_without_question_text(self) -> None:
        http = FakeHttpClient([FakeResponse(200), FakeResponse(201, [RECORD])])
        repository = SupabaseQuestionTtsRepository(SETTINGS, http)

        with patch("app.services.question_tts_persistence.uuid4", return_value=AUDIO_ID):
            record = repository.create(USER, FakeGeneratedQuestionAudio(valid_wav(), 1200))

        self.assertEqual(record.audio_id, str(AUDIO_ID))
        upload, insert = http.requests
        self.assertEqual(upload["headers"]["Authorization"], "Bearer user-access-token")
        self.assertTrue(upload["url"].endswith(f"/storage/v1/object/question-tts-audio/{AUDIO_PATH}"))
        self.assertEqual(upload["headers"]["Content-Type"], "audio/wav")
        self.assertEqual(upload["headers"]["x-upsert"], "false")
        self.assertEqual(insert["json"], {
            "id": str(AUDIO_ID),
            "user_id": "user-1",
            "audio_path": AUDIO_PATH,
            "duration_ms": 1200,
        })

    def test_db_insert_failure_removes_uploaded_object(self) -> None:
        http = FakeHttpClient([FakeResponse(200), FakeResponse(500), FakeResponse(200)])
        repository = SupabaseQuestionTtsRepository(SETTINGS, http)

        with patch("app.services.question_tts_persistence.uuid4", return_value=AUDIO_ID):
            with self.assertRaises(QuestionTtsPersistenceError) as raised:
                repository.create(USER, FakeGeneratedQuestionAudio(valid_wav(), 1200))

        self.assertEqual(raised.exception.code, "PERSISTENCE_FAILED")
        self.assertEqual([request["method"] for request in http.requests], ["POST", "POST", "DELETE"])
        self.assertEqual(http.requests[2]["json"], {"prefixes": [AUDIO_PATH]})

    def test_storage_failure_does_not_insert_database_row(self) -> None:
        http = FakeHttpClient([FakeResponse(403)])
        repository = SupabaseQuestionTtsRepository(SETTINGS, http)

        with self.assertRaises(QuestionTtsPersistenceError):
            repository.create(USER, FakeGeneratedQuestionAudio(valid_wav(), 1200))

        self.assertEqual(len(http.requests), 1)

    def test_other_users_audio_id_is_not_downloaded(self) -> None:
        http = FakeHttpClient([FakeResponse(200, [])])
        repository = SupabaseQuestionTtsRepository(SETTINGS, http)

        with self.assertRaises(KeyError):
            repository.read_wav(USER, "another-users-audio", datetime(2026, 8, 19, tzinfo=UTC))

        self.assertEqual(len(http.requests), 1)
        self.assertIn("/rest/v1/question_tts_audio?id=eq.another-users-audio", http.requests[0]["url"])

    def test_expired_audio_is_not_downloaded(self) -> None:
        expired_record = {**RECORD, "expires_at": "2026-08-18T00:00:00Z"}
        http = FakeHttpClient([FakeResponse(200, [expired_record])])
        repository = SupabaseQuestionTtsRepository(SETTINGS, http)

        with self.assertRaises(KeyError):
            repository.read_wav(USER, str(AUDIO_ID), datetime(2026, 8, 19, tzinfo=UTC))

        self.assertEqual(len(http.requests), 1)

    def test_row_for_a_different_user_is_not_downloaded_even_if_returned_by_storage_query(self) -> None:
        other_users_record = {**RECORD, "user_id": "user-2"}
        http = FakeHttpClient([FakeResponse(200, [other_users_record])])
        repository = SupabaseQuestionTtsRepository(SETTINGS, http)

        with self.assertRaises(KeyError):
            repository.read_wav(USER, str(AUDIO_ID), datetime(2026, 8, 19, tzinfo=UTC))

        self.assertEqual(len(http.requests), 1)


class SupabaseExpiredQuestionTtsRepositoryTest(unittest.TestCase):
    def test_cleanup_deletes_storage_before_database_row(self) -> None:
        http = FakeHttpClient([FakeResponse(200), FakeResponse(204)])
        repository = SupabaseExpiredQuestionTtsRepository(SETTINGS, http)

        repository.delete_expired(RECORD)

        self.assertEqual([request["method"] for request in http.requests], ["DELETE", "DELETE"])
        self.assertTrue(http.requests[0]["url"].endswith("/storage/v1/object/question-tts-audio"))
        self.assertIn(f"/rest/v1/question_tts_audio?id=eq.{AUDIO_ID}", http.requests[1]["url"])

    def test_storage_delete_failure_marks_row_and_keeps_it(self) -> None:
        http = FakeHttpClient([FakeResponse(500), FakeResponse(204)])
        repository = SupabaseExpiredQuestionTtsRepository(SETTINGS, http)

        with self.assertRaises(QuestionTtsPersistenceError) as raised:
            repository.delete_expired(RECORD)
        repository.mark_cleanup_failed(str(AUDIO_ID), raised.exception.code)

        self.assertEqual(raised.exception.code, "STORAGE_DELETE_FAILED")
        self.assertEqual([request["method"] for request in http.requests], ["DELETE", "PATCH"])
        self.assertNotIn("/rest/v1/question_tts_audio?id=eq.", http.requests[0]["url"])
        self.assertEqual(http.requests[1]["json"]["cleanup_error_code"], "STORAGE_DELETE_FAILED")


if __name__ == "__main__":
    unittest.main()
