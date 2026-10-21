from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.expired_question_tts_cleanup import cleanup_expired_question_tts_audio
from app.services.question_tts_persistence import QuestionTtsPersistenceError


class FakeCleanupRepository:
    def __init__(self, rows: list[dict[str, object]], failures: dict[str, str] | None = None) -> None:
        self.rows = rows
        self.failures = failures or {}
        self.deleted: list[str] = []
        self.marked: list[tuple[str, str]] = []

    def list_expired(self) -> list[dict[str, object]]:
        return self.rows

    def delete_expired(self, row: dict[str, object]) -> None:
        audio_id = row["id"]
        if audio_id in self.failures:
            raise QuestionTtsPersistenceError(self.failures[audio_id], "storage failed")
        self.deleted.append(audio_id)

    def mark_cleanup_failed(self, audio_id: str, code: str) -> None:
        self.marked.append((audio_id, code))


class ExpiredQuestionTtsCleanupTest(unittest.TestCase):
    def test_cleanup_deletes_every_expired_audio_and_counts_success(self) -> None:
        repository = FakeCleanupRepository([{"id": "audio-1"}, {"id": "audio-2"}])

        summary = cleanup_expired_question_tts_audio(repository)

        self.assertEqual(repository.deleted, ["audio-1", "audio-2"])
        self.assertEqual(repository.marked, [])
        self.assertEqual((summary.deleted_audio, summary.failed_audio), (2, 0))

    def test_storage_failure_keeps_row_and_records_only_a_safe_error_code(self) -> None:
        repository = FakeCleanupRepository([{"id": "audio-1"}], {"audio-1": "STORAGE_DELETE_FAILED"})

        summary = cleanup_expired_question_tts_audio(repository)

        self.assertEqual(repository.deleted, [])
        self.assertEqual(repository.marked, [("audio-1", "STORAGE_DELETE_FAILED")])
        self.assertEqual((summary.deleted_audio, summary.failed_audio), (0, 1))

    def test_invalid_record_is_counted_without_marking_an_unknown_id(self) -> None:
        repository = FakeCleanupRepository([{}])

        summary = cleanup_expired_question_tts_audio(repository)

        self.assertEqual(repository.deleted, [])
        self.assertEqual(repository.marked, [])
        self.assertEqual((summary.deleted_audio, summary.failed_audio), (0, 1))


if __name__ == "__main__":
    unittest.main()
