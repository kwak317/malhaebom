from __future__ import annotations

import importlib.util
import json
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.question_tts_stream import GeneratedQuestionPcm

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "evaluate_question_tts.py"


def load_evaluation_module():
    spec = importlib.util.spec_from_file_location("question_tts_evaluation", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("evaluation script could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeStreamSynthesizer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def stream(self, text: str, cancel: threading.Event):
        self.calls.append(text)
        yield GeneratedQuestionPcm(
            pcm16=struct.pack("<2400h", *([1024] * 2400)),
            is_final=True,
        )


class EvaluateQuestionTtsTest(unittest.TestCase):
    def test_evaluation_records_stream_latency_stop_reason_and_manual_review_without_sensitive_input(self) -> None:
        evaluation = load_evaluation_module()
        synthesizer = FakeStreamSynthesizer()
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "question-tts-test"
            records = evaluation.run_stream_evaluation(synthesizer, output_dir, gpu_peak_bytes=lambda: 0)
            persisted_records = [
                json.loads(line)
                for line in (output_dir / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

        self.assertEqual(len(records), 13)
        self.assertEqual(len(synthesizer.calls), 13)
        self.assertTrue(all(call.endswith("//") for call in synthesizer.calls))
        self.assertEqual(persisted_records, records)
        required = {
            "requestId",
            "firstAudioSeconds",
            "generationSeconds",
            "audioDurationSeconds",
            "rtf",
            "gpuPeakAllocatedBytes",
            "stopReason",
            "wavFormatValid",
            "manualReview",
        }
        self.assertTrue(all(required <= record.keys() for record in records))
        self.assertTrue(all("text" not in record and "modelPath" not in record and "userId" not in record for record in records))
        self.assertTrue(all(record["stopReason"] == "model_eos" for record in records))
        self.assertTrue(all(record["manualReview"] == "pending" and record["wavFormatValid"] for record in records))
        self.assertEqual(summary["requestCount"], 13)
        self.assertEqual(summary["manualReview"], "pending")

    def test_evaluation_refuses_to_overwrite_an_existing_result_directory(self) -> None:
        evaluation = load_evaluation_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "existing"
            output_dir.mkdir()
            with self.assertRaises(FileExistsError):
                evaluation.run_stream_evaluation(FakeStreamSynthesizer(), output_dir, gpu_peak_bytes=lambda: 0)


if __name__ == "__main__":
    unittest.main()
