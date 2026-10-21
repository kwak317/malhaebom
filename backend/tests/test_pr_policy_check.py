from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_pr_policy import (
    analyze_diff,
    check_pr_description_for_rationale,
    evaluate_policy,
    is_exception_file,
    parse_numstat_line,
)


class CheckPrPolicyTest(unittest.TestCase):
    def test_parse_numstat_line(self):
        # Valid lines
        self.assertEqual(parse_numstat_line("10\t5\tbackend/main.py"), (10, 5, "backend/main.py"))
        # Binary file
        self.assertEqual(parse_numstat_line("-\t-\timage.png"), (0, 0, "image.png"))
        # Malformed line
        self.assertIsNone(parse_numstat_line("invalid_line"))

    def test_is_exception_file(self):
        # Exception files
        self.assertTrue(is_exception_file("docs/worklogs/2026-09-20_test.md"))
        self.assertTrue(is_exception_file("package-lock.json"))
        self.assertTrue(is_exception_file("poetry.lock"))
        self.assertTrue(is_exception_file("evals/results/comparison.json"))
        self.assertTrue(is_exception_file("local-results/run.json"))
        self.assertTrue(is_exception_file("evals/dataset.v2.jsonl"))

        # Review core files: specs, evaluation reports, core docs, agents, and experiment docs/plans/methods
        self.assertFalse(is_exception_file("backend/main.py"))
        self.assertFalse(is_exception_file("backend/tests/test_api.py"))
        self.assertFalse(is_exception_file("docs/specs/test-spec.md"))
        self.assertFalse(is_exception_file("AGENTS.md"))
        self.assertFalse(is_exception_file("EVAL_REPORT.md"))
        self.assertFalse(is_exception_file("docs/experiments/README.md"))
        self.assertFalse(is_exception_file("docs/experiments/2026-09-21_candidate-30case-extension.md"))
        self.assertFalse(is_exception_file("docs/experiments/stt/2026-09-21_clean-continuation-lr2e-5.md"))

    def test_analyze_diff_distinguishes_core_and_exceptions(self):
        stats = [
            (100, 10, "backend/main.py"),  # Core: 110
            (50, 5, "backend/tests/test_main.py"),  # Core: 55
            (200, 0, "docs/worklogs/2026-09-21_worklog.md"),  # Exception: 200
            (100, 0, "package-lock.json"),  # Exception: 100
        ]
        res = analyze_diff(stats)
        self.assertEqual(res["core_diff"], 165)
        self.assertEqual(res["except_diff"], 300)
        self.assertEqual(res["total_diff"], 465)

    def test_evaluate_policy_under_recommended_limit(self):
        analysis = {
            "total_diff": 450,
            "total_add": 400,
            "total_del": 50,
            "core_diff": 350,
            "core_add": 300,
            "core_del": 50,
            "except_diff": 100,
            "except_add": 100,
            "except_del": 0,
            "core_files": [("backend/main.py", 300, 50, 350)],
            "except_files": [("docs/worklogs/test.md", 100, 0, 100)],
        }
        passed, messages = evaluate_policy(analysis)
        self.assertTrue(passed)
        self.assertTrue(any("within recommended limit" in m for m in messages))

    def test_evaluate_policy_between_recommended_and_hard_limit(self):
        analysis = {
            "total_diff": 650,
            "total_add": 600,
            "total_del": 50,
            "core_diff": 550,
            "core_add": 500,
            "core_del": 50,
            "except_diff": 100,
            "except_add": 100,
            "except_del": 0,
            "core_files": [("backend/main.py", 500, 50, 550)],
            "except_files": [],
        }
        # Without rationale in PR body
        passed, messages = evaluate_policy(analysis, pr_body=None)
        self.assertTrue(passed)  # CLI advisory without pr-body
        self.assertTrue(any("exceeds recommended guideline" in m for m in messages))

        # With empty pr_body -> fails
        passed, messages = evaluate_policy(analysis, pr_body="")
        self.assertFalse(passed)

        # With valid rationale in pr_body -> passes
        valid_body = "## Summary\n\n## 기준 초과 사유\n이 작업은 핵심 인터페이스 변경과 이에 따른 통합 테스트가 결합되어 있어 분리할 경우 검증이 불가능합니다."
        passed, messages = evaluate_policy(analysis, pr_body=valid_body)
        self.assertTrue(passed)
        self.assertTrue(any("Documented rationale found" in m for m in messages))

    def test_evaluate_policy_exceeding_hard_limit_fails(self):
        analysis = {
            "total_diff": 1000,
            "total_add": 900,
            "total_del": 100,
            "core_diff": 850,
            "core_add": 800,
            "core_del": 50,
            "except_diff": 150,
            "except_add": 100,
            "except_del": 50,
            "core_files": [("backend/main.py", 800, 50, 850)],
            "except_files": [],
        }
        passed, messages = evaluate_policy(analysis, pr_body="기준 초과 사유 작성 완료")
        self.assertFalse(passed)
        self.assertTrue(any("exceeds the hard limit of 800" in m for m in messages))


if __name__ == "__main__":
    unittest.main()

