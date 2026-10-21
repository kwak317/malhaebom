from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.question_tts_persistence import QuestionTtsPersistenceError


@dataclass(frozen=True)
class QuestionTtsCleanupSummary:
    deleted_audio: int = 0
    failed_audio: int = 0


def cleanup_expired_question_tts_audio(repository: Any) -> QuestionTtsCleanupSummary:
    deleted = failed = 0
    for row in repository.list_expired():
        audio_id = row.get("id")
        try:
            repository.delete_expired(row)
            deleted += 1
        except (QuestionTtsPersistenceError, KeyError) as error:
            if isinstance(audio_id, str) and isinstance(error, QuestionTtsPersistenceError):
                try:
                    repository.mark_cleanup_failed(audio_id, error.code)
                except QuestionTtsPersistenceError:
                    pass
            failed += 1
    return QuestionTtsCleanupSummary(deleted_audio=deleted, failed_audio=failed)
