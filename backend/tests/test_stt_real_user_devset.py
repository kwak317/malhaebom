from __future__ import annotations

import importlib.util
from unittest.mock import patch
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREP = load_module("prepare_stt_real_user_devset", "prepare_stt_real_user_devset.py")


class RealUserDevsetPrepTest(unittest.TestCase):
    def test_parse_references(self) -> None:
        text = """# title

### 01. one
첫 번째 문장입니다.

### 02. two
두 번째 문장입니다.
"""
        self.assertEqual(
            PREP.parse_references(text),
            {1: "첫 번째 문장입니다.", 2: "두 번째 문장입니다."},
        )

    def test_audio_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "audio.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("소리 녹음/소리 녹음 (1).m4a", b"a")
                archive.writestr("소리 녹음/소리 녹음 (2).m4a", b"b")
            with zipfile.ZipFile(archive_path) as archive:
                entries = PREP.audio_entries(archive)
        self.assertEqual(sorted(entries), [1, 2])

    def test_group_boundaries(self) -> None:
        self.assertEqual(PREP.group_for_index(1), "general-interview")
        self.assertEqual(PREP.group_for_index(11), "technical")
        self.assertEqual(PREP.group_for_index(19), "numbers-english-stress")
        self.assertEqual(PREP.group_for_index(30), "natural-long")

    def test_duplicate_script_index_is_rejected(self) -> None:
        text = """### 01. first
첫 번째

### 01. duplicate
중복
"""
        with self.assertRaisesRegex(ValueError, "duplicate script index"):
            PREP.parse_references(text)

    def test_empty_fingerprint_bypass_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            PREP.validate_expected_sha256("audio ZIP", "a" * 64, "")

    def test_fingerprint_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "fingerprint mismatch"):
            PREP.validate_expected_sha256(
                "reference script",
                "a" * 64,
                "b" * 64,
            )

    def test_alternate_expected_hash_cannot_replace_canonical_devset(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "canonical"):
            PREP.validate_canonical_fingerprints("a" * 64, "b" * 64)

    def test_cli_rejects_expected_hash_override(self) -> None:
        with patch.object(sys, "argv", ["prepare", "--audio-zip", "audio.zip", "--expected-zip-sha256", "a" * 64]):
            with self.assertRaises(SystemExit) as error:
                PREP.parse_args()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
