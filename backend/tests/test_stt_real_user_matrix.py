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
    "run_stt_real_user_matrix",
    SCRIPTS / "run_stt_real_user_matrix.py",
)
assert spec and spec.loader
MATRIX = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MATRIX)


class RealUserMatrixTest(unittest.TestCase):
    def test_large_model_provenance_is_pinned(self) -> None:
        class Args:
            models = ["large-v3-turbo"]
            large_model = MATRIX.LARGE_MODEL_REPO
            large_model_revision = MATRIX.LARGE_MODEL_REVISION

        provenance = MATRIX.model_provenance(Args())
        self.assertEqual(
            provenance["large-v3-turbo"],
            {
                "kind": "huggingface",
                "repo_id": MATRIX.LARGE_MODEL_REPO,
                "revision": "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
            },
        )

    def test_local_model_provenance_records_content_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for name in (
                "config.json",
                "model.bin",
                "tokenizer.json",
                "vocabulary.json",
                "preprocessor_config.json",
            ):
                (path / name).write_bytes(name.encode("utf-8"))

            class Args:
                models = ["b0"]
                b0_model = path

            provenance = MATRIX.model_provenance(Args())
            self.assertEqual(provenance["b0"]["kind"], "local_ct2")
            self.assertEqual(provenance["b0"]["path"], str(path.resolve()))
            self.assertRegex(
                provenance["b0"]["fingerprint_sha256"],
                r"^[0-9a-f]{64}$",
            )

    def test_resume_rejects_changed_devset_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "audio").mkdir()
            audio = root / "audio/01.m4a"
            audio.write_bytes(b"first")
            row = {"id": "real-01", "audio": "audio/01.m4a", "reference": "원본", "group": "general-interview"}
            manifest = root / "manifest.jsonl"
            manifest.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            original = MATRIX.devset_provenance(root, [row])
            record = {**row, "prediction": "원본", "processing_time_sec": 0.1, "audio_duration_sec": 1.0, "rtf": 0.1}
            metrics = root / "metrics.json"
            (root / "predictions.json").write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")
            class Args:
                resume = True
                device = "cpu"
                compute_type = "int8"
            run = {"model": "b0", "model_source": "model", "model_provenance": {"id": "model"}, "beam_size": 1, "device": "cpu", "compute_type": "int8", "row_count": 1, "word_timestamps": True, "devset_provenance": original, "model_load_sec": 0.1}
            payload = {"schema_version": 2, "run": run, "scores": MATRIX.score_groups([record]), "timing": MATRIX.timing_metrics([record])}
            metrics.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            def resumed(devset):
                return MATRIX.matching_completed_metrics(metrics, model="b0", model_source="model", model_provenance={"id": "model"}, beam_size=1, args=Args(), row_count=1, devset=devset)
            self.assertIsNotNone(resumed(original))
            changed = {**row, "reference": "변경"}
            manifest.write_text(json.dumps(changed, ensure_ascii=False) + "\n", encoding="utf-8")
            self.assertIsNone(resumed(MATRIX.devset_provenance(root, [changed])))
            manifest.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            audio.write_bytes(b"second")
            self.assertIsNone(resumed(MATRIX.devset_provenance(root, [row])))


if __name__ == "__main__":
    unittest.main()
