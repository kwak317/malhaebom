from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location(
    "run_stt_real_user_prompt_ab",
    SCRIPTS / "run_stt_real_user_prompt_ab.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PromptHintAbTest(unittest.TestCase):
    def test_short_alias_does_not_match_inside_long_word(self) -> None:
        pattern = MODULE.alias_regex("PR")
        self.assertIsNone(pattern.search("project"))
        self.assertIsNotNone(pattern.search("PR이 생성됩니다"))

    def test_spacing_alias_matches(self) -> None:
        self.assertTrue(MODULE.text_has_alias("Fast API를 사용했습니다", ["FastAPI", "Fast API"]))
        self.assertTrue(MODULE.text_has_alias("C Translate 2를 사용했습니다", ["CTranslate2", "C Translate 2"]))

    def test_term_metrics_counts_hit_miss_and_false_insertion(self) -> None:
        hints = {
            "terms": [
                {"canonical": "Docker", "aliases": ["Docker"]},
                {"canonical": "PR", "aliases": ["PR"]},
            ]
        }
        records = [
            {"id": "a", "reference": "Docker를 사용합니다", "prediction": "Docker를 사용합니다"},
            {"id": "b", "reference": "일반 답변입니다", "prediction": "PR 일반 답변입니다"},
        ]
        result = MODULE.term_metrics(records, hints)
        self.assertEqual(result["target_row_terms"], 1)
        self.assertEqual(result["hit_row_terms"], 1)
        self.assertEqual(result["recall_percent"], 100.0)
        self.assertEqual(result["false_insertion_row_terms"], 1)

    def test_mode_kwargs(self) -> None:
        hints = {"initial_prompt": "prompt", "hotwords": "words"}
        self.assertEqual(MODULE.mode_kwargs("none", hints), {})
        self.assertEqual(
            MODULE.mode_kwargs("initial_prompt", hints),
            {"initial_prompt": "prompt"},
        )
        self.assertEqual(MODULE.mode_kwargs("hotwords", hints), {"hotwords": "words"})

    def test_resume_rejects_changed_devset_fingerprint(self) -> None:
        original = {
            "row_count": 1,
            "manifest_sha256": "a" * 64,
            "audio_set_sha256": "b" * 64,
            "data_fingerprint_sha256": "c" * 64,
        }
        changed = {**original, "manifest_sha256": "d" * 64}

        class Args:
            resume = True
            model = MODULE.matrix.LARGE_MODEL_REPO
            model_revision = MODULE.matrix.LARGE_MODEL_REVISION
            beam_size = 1
            device = "cuda"
            compute_type = "float16"

        subset = {
            "spoken_form_normalized": {"cer_percent": 0.0, "wer_percent": 0.0},
            "raw": {"cer_percent": 0.0, "wer_percent": 0.0},
        }
        payload = {
            "schema_version": 2,
            "run": {
                "mode": "none",
                "model": Args.model,
                "model_revision": Args.model_revision,
                "beam_size": 1,
                "device": "cuda",
                "compute_type": "float16",
                "hints_sha256": "e" * 64,
                "devset_provenance": original,
                "row_count": 1,
            },
            "scores": {
                "overall": subset,
                "core_excluding_stress": subset,
                "groups": {},
            },
            "term_metrics": {
                "recall_percent": 100.0,
                "false_insertion_row_terms": 0,
            },
            "timing": {
                "aggregate_rtf": 0.1,
                "latency_p50_sec": 0.2,
                "latency_p95_sec": 0.3,
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics = root / "metrics.json"
            metrics.write_text(json.dumps(payload), encoding="utf-8")
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
                MODULE.matching_completed(
                    metrics,
                    mode="none",
                    args=Args(),
                    hints_sha256="e" * 64,
                    devset=original,
                    row_count=1,
                )
            )
            self.assertIsNone(
                MODULE.matching_completed(
                    metrics,
                    mode="none",
                    args=Args(),
                    hints_sha256="e" * 64,
                    devset=changed,
                    row_count=1,
                )
            )


if __name__ == "__main__":
    unittest.main()
