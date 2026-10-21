from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "score_stt_spoken_form.py"
SPEC = importlib.util.spec_from_file_location("score_stt_spoken_form", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SpokenFormScorerTest(unittest.TestCase):
    def test_acronym_pronunciation_is_equivalent(self) -> None:
        self.assertEqual(
            MODULE.normalize_spoken_form("CER과 WER"),
            MODULE.normalize_spoken_form("씨에알과 더블유에알"),
        )

    def test_numeric_reading_is_equivalent(self) -> None:
        self.assertEqual(
            MODULE.normalize_spoken_form("1,233개와 2026년"),
            MODULE.normalize_spoken_form("천이백삼십삼개와 이천 이십육년"),
        )

    def test_genuine_recognition_error_is_not_repaired(self) -> None:
        self.assertNotEqual(
            MODULE.normalize_spoken_form("Docker와 PR"),
            MODULE.normalize_spoken_form("덕허와 피아리"),
        )


if __name__ == "__main__":
    unittest.main()
