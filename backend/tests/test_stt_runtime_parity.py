from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location(
    "run_stt_runtime_parity",
    SCRIPTS / "run_stt_runtime_parity.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimeParityTest(unittest.TestCase):
    def test_runtime_matrix_matches_service_and_experiment_conditions(self) -> None:
        self.assertEqual(
            MODULE.RUNTIMES,
            {
                "cpu-int8": {"device": "cpu", "compute_type": "int8"},
                "cuda-float16": {"device": "cuda", "compute_type": "float16"},
            },
        )

    def test_matching_completed_binds_runtime_and_provenance(self) -> None:
        captured = {}

        def fake_loader(path, *, expected_run, row_count, summary_validator):
            captured["path"] = path
            captured["expected_run"] = expected_run
            captured["row_count"] = row_count
            captured["summary_validator"] = summary_validator
            return {"ok": True}

        original = MODULE.load_matching_completed_metrics
        MODULE.load_matching_completed_metrics = fake_loader
        try:
            class Args:
                resume = True
                model = "large-model"
                model_revision = "immutable-revision"
                beam_size = 1

            hints = {"sha256": "hint-sha"}
            devset = {"manifest_sha256": "manifest-sha"}
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "metrics.json"
                path.write_text("{}", encoding="utf-8")
                result = MODULE.matching_completed(
                    path,
                    runtime="cpu-int8",
                    args=Args(),
                    hints=hints,
                    devset=devset,
                    row_count=30,
                )
        finally:
            MODULE.load_matching_completed_metrics = original

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["row_count"], 30)
        self.assertEqual(
            captured["expected_run"],
            {
                "runtime": "cpu-int8",
                "model": "large-model",
                "model_revision": "immutable-revision",
                "beam_size": 1,
                "device": "cpu",
                "compute_type": "int8",
                "hint_mode": "initial_prompt",
                "hints_sha256": "hint-sha",
                "devset_provenance": devset,
                "row_count": 30,
            },
        )

    def test_summary_row_exposes_accuracy_and_latency(self) -> None:
        score = {
            "cer_percent": 1.0,
            "wer_percent": 2.0,
        }
        payload = {
            "run": {
                "runtime": "cuda-float16",
                "device": "cuda",
                "compute_type": "float16",
                "model_load_sec": 1.5,
            },
            "scores": {
                "overall": {
                    "raw": score,
                    "spoken_form_normalized": score,
                },
                "core_excluding_stress": {
                    "spoken_form_normalized": {
                        "cer_percent": 3.0,
                        "wer_percent": 4.0,
                    }
                },
                "groups": {
                    "numbers-english-stress": {
                        "spoken_form_normalized": {
                            "cer_percent": 5.0,
                            "wer_percent": 6.0,
                        }
                    }
                },
            },
            "term_metrics": {
                "recall_percent": 90.0,
                "false_insertion_row_terms": 0,
            },
            "timing": {
                "aggregate_rtf": 0.02,
                "latency_p50_sec": 0.25,
                "latency_p95_sec": 0.5,
            },
        }

        row = MODULE.summary_row(payload)

        self.assertEqual(row["runtime"], "cuda-float16")
        self.assertEqual(row["core_normalized_cer"], 3.0)
        self.assertEqual(row["stress_normalized_wer"], 6.0)
        self.assertEqual(row["term_recall"], 90.0)
        self.assertEqual(row["latency_p95_sec"], 0.5)
        self.assertEqual(row["model_load_sec"], 1.5)


if __name__ == "__main__":
    unittest.main()
