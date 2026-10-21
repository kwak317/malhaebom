from __future__ import annotations

import importlib.util
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.expired_question_tts_cleanup import QuestionTtsCleanupSummary
from app.services.question_tts_persistence import QuestionTtsPersistenceError

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "cleanup_expired_question_tts_audio.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("question_tts_cleanup_script", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cleanup script could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CleanupExpiredQuestionTtsAudioScriptTest(unittest.TestCase):
    def test_success_reports_counts_without_exposing_settings(self) -> None:
        script = load_script_module()
        output = StringIO()
        with (
            patch.object(script.SupabaseSettings, "from_env", return_value=object()),
            patch.object(script, "SupabaseExpiredQuestionTtsRepository", return_value=object()),
            patch.object(script, "cleanup_expired_question_tts_audio", return_value=QuestionTtsCleanupSummary(2, 0)),
            redirect_stdout(output),
        ):
            result = script.main()

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().strip(), "question tts cleanup completed: deleted=2, failed=0")

    def test_failure_returns_nonzero_without_printing_internal_error(self) -> None:
        script = load_script_module()
        output = StringIO()
        with (
            patch.object(script.SupabaseSettings, "from_env", side_effect=QuestionTtsPersistenceError("CONFIGURATION_ERROR", "internal details")),
            redirect_stdout(output),
        ):
            result = script.main()

        self.assertEqual(result, 1)
        self.assertEqual(output.getvalue().strip(), "question tts cleanup unavailable")


if __name__ == "__main__":
    unittest.main()
