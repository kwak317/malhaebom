from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SPEC = importlib.util.spec_from_file_location(
    "benchmark_analysis_e2e",
    SCRIPTS / "benchmark_analysis_e2e.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BenchmarkAnalysisE2ETest(unittest.TestCase):
    def test_percentile(self) -> None:
        self.assertEqual(MODULE.percentile([1.0], 0.95), 1.0)
        self.assertAlmostEqual(MODULE.percentile([1.0, 2.0, 3.0], 0.5), 2.0)
        self.assertAlmostEqual(MODULE.percentile([1.0, 2.0, 3.0], 0.95), 2.9)

    def test_summary_excludes_warmup(self) -> None:
        records = [
            MODULE.RunResult(
                1, True, "a.wav", "j1", "s1",
                1.0, 9.0, 10.0, 2, "completed",
                8.0, 10.0, 0.8, "m", "cpu", "int8",
            ),
            MODULE.RunResult(
                2, False, "a.wav", "j2", "s1",
                0.2, 2.8, 3.0, 3, "completed",
                2.5, 10.0, 0.25, "m", "cpu", "int8",
            ),
            MODULE.RunResult(
                3, False, "b.wav", "j3", "s1",
                0.3, 3.7, 4.0, 4, "completed",
                3.5, 10.0, 0.35, "m", "cpu", "int8",
            ),
        ]

        summary = MODULE.summarize(records)

        self.assertEqual(summary["measured_runs"], 2)
        self.assertEqual(summary["completed_runs"], 2)
        self.assertEqual(summary["failed_runs"], 0)
        self.assertAlmostEqual(summary["total_sec"]["p50"], 3.5)
        self.assertAlmostEqual(summary["server_stt_sec"]["p50"], 3.0)

    def test_question_fields_custom(self) -> None:
        class Args:
            question_type = "custom"
            question_id = None
            custom_question_text = "  Python 경험을 설명해 주세요.  "

        self.assertEqual(
            MODULE.question_fields(Args()),
            {
                "question_type": "custom",
                "attempt_no": "1",
                "custom_question_text": "Python 경험을 설명해 주세요.",
            },
        )

    def test_validate_requires_one_or_two_requirements_for_posting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "sample.wav"
            audio.write_bytes(b"fake")
            args = SimpleNamespace(
                token="token",
                runs=1,
                warmup=0,
                poll_interval=0.25,
                timeout=10.0,
                request_timeout=10.0,
                audio=[audio],
                practice_session_id=None,
                job_posting_id="posting",
                requirement_id=[],
                question_type="custom",
                question_id=None,
                custom_question_text="질문",
                keep_jobs=False,
            )

            with self.assertRaisesRegex(ValueError, "one or two"):
                MODULE.validate_args(args)

    def test_validate_rejects_repeated_keep_jobs_on_one_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "sample.wav"
            audio.write_bytes(b"fake")
            args = SimpleNamespace(
                token="token",
                runs=2,
                warmup=0,
                poll_interval=0.25,
                timeout=10.0,
                request_timeout=10.0,
                audio=[audio],
                practice_session_id=None,
                job_posting_id="posting",
                requirement_id=["requirement"],
                question_type="custom",
                question_id=None,
                custom_question_text="질문",
                keep_jobs=True,
            )

            with self.assertRaisesRegex(ValueError, "cannot repeat attempt 1"):
                MODULE.validate_args(args)


if __name__ == "__main__":
    unittest.main()
