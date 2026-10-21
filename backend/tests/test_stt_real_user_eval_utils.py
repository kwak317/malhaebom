from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "stt_real_user_eval_utils",
    SCRIPTS / "stt_real_user_eval_utils.py",
)
assert spec and spec.loader
UTILS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(UTILS)


class SttRealUserEvalUtilsTest(unittest.TestCase):
    def test_devset_fingerprint_changes_when_manifest_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "audio").mkdir()
            (root / "audio/01.m4a").write_bytes(b"audio")
            manifest = root / "manifest.jsonl"
            row = {
                "id": "real-01",
                "audio": "audio/01.m4a",
                "reference": "원본",
                "group": "general-interview",
            }
            manifest.write_text(
                json.dumps(row, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            first = UTILS.devset_provenance(root, [row])

            changed = {**row, "reference": "변경된 원본"}
            manifest.write_text(
                json.dumps(changed, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            second = UTILS.devset_provenance(root, [changed])

        self.assertNotEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(first["audio_set_sha256"], second["audio_set_sha256"])
        self.assertNotEqual(
            first["data_fingerprint_sha256"],
            second["data_fingerprint_sha256"],
        )

    def test_devset_fingerprint_changes_when_audio_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "audio").mkdir()
            audio = root / "audio/01.m4a"
            audio.write_bytes(b"audio-v1")
            row = {
                "id": "real-01",
                "audio": "audio/01.m4a",
                "reference": "원본",
                "group": "general-interview",
            }
            (root / "manifest.jsonl").write_text(
                json.dumps(row, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            first = UTILS.devset_provenance(root, [row])
            audio.write_bytes(b"audio-v2")
            second = UTILS.devset_provenance(root, [row])

        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertNotEqual(first["audio_set_sha256"], second["audio_set_sha256"])

    def test_percentile_and_timing(self) -> None:
        self.assertAlmostEqual(UTILS.percentile([1.0, 2.0, 3.0], 0.95), 2.9)
        result = UTILS.timing_metrics([
            {"processing_time_sec": 1.0, "audio_duration_sec": 10.0, "rtf": 0.1},
            {"processing_time_sec": 2.0, "audio_duration_sec": 10.0, "rtf": 0.2},
        ])
        self.assertAlmostEqual(result["aggregate_rtf"], 0.15)
        self.assertAlmostEqual(result["latency_p50_sec"], 1.5)

    def test_score_groups_separates_stress(self) -> None:
        records = [
            {"id": "real-01", "group": "general-interview", "reference": "안녕하세요", "prediction": "안녕하세요"},
            {"id": "real-19", "group": "numbers-english-stress", "reference": "Docker", "prediction": "덕허"},
        ]
        scores = UTILS.score_groups(records)
        self.assertEqual(scores["core_excluding_stress"]["raw"]["cer_percent"], 0.0)
        self.assertGreater(scores["overall"]["raw"]["cer_percent"], 0.0)

    def test_local_ct2_fingerprint_changes_with_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for name in UTILS.CT2_MODEL_FILES:
                (path / name).write_bytes(name.encode("utf-8"))
            before = UTILS.ct2_model_fingerprint(path)
            (path / "model.bin").write_bytes(b"changed")
            after = UTILS.ct2_model_fingerprint(path)
        self.assertNotEqual(before, after)

    def test_completed_metrics_rejects_corrupt_or_missing_predictions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "metrics.json"
            path.write_text("{", encoding="utf-8")
            self.assertIsNone(
                UTILS.load_matching_completed_metrics(
                    path,
                    expected_run={"model": "c2"},
                    row_count=1,
                    summary_validator=lambda _: None,
                )
            )

            path.write_text(
                json.dumps({"schema_version": 2, "run": {"model": "c2"}}),
                encoding="utf-8",
            )
            self.assertIsNone(
                UTILS.load_matching_completed_metrics(
                    path,
                    expected_run={"model": "c2"},
                    row_count=1,
                    summary_validator=lambda _: None,
                )
            )

    def test_completed_metrics_requires_expected_run_and_complete_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "metrics.json"
            path.write_text(
                json.dumps({"schema_version": 2, "run": {"model": "c2", "fingerprint": "a"}}),
                encoding="utf-8",
            )
            (root / "predictions.json").write_text(
                json.dumps([{
                    "id": "real-01",
                    "reference": "a",
                    "prediction": "a",
                    "processing_time_sec": 0.1,
                    "audio_duration_sec": 1.0,
                }]),
                encoding="utf-8",
            )
            self.assertIsNotNone(
                UTILS.load_matching_completed_metrics(
                    path,
                    expected_run={"model": "c2", "fingerprint": "a"},
                    row_count=1,
                    summary_validator=lambda _: None,
                )
            )
            self.assertIsNone(
                UTILS.load_matching_completed_metrics(
                    path,
                    expected_run={"model": "c2", "fingerprint": "b"},
                    row_count=1,
                    summary_validator=lambda _: None,
                )
            )


if __name__ == "__main__":
    unittest.main()
