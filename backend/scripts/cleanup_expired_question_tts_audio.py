from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.supabase_settings import SupabaseSettings, SupabaseSettingsError
from app.services.expired_question_tts_cleanup import cleanup_expired_question_tts_audio
from app.services.question_tts_persistence import (
    QuestionTtsPersistenceError,
    SupabaseExpiredQuestionTtsRepository,
)


def main() -> int:
    try:
        settings = SupabaseSettings.from_env(require_service_role=True)
        summary = cleanup_expired_question_tts_audio(SupabaseExpiredQuestionTtsRepository(settings))
    except (SupabaseSettingsError, QuestionTtsPersistenceError):
        print("question tts cleanup unavailable")
        return 1
    print(f"question tts cleanup completed: deleted={summary.deleted_audio}, failed={summary.failed_audio}")
    return 0 if summary.failed_audio == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
