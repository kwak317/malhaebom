"""Gemini v5 사람 검토 양식 생성은 외부 API를 호출하지 않는다."""

import unittest

from evals.build_gemini_v5_human_review import build_review_pack


class GeminiV5HumanReviewPackTest(unittest.TestCase):
    def test_selects_only_valid_attempts_with_automatic_mismatches(self):
        report = {
            "attempts": [
                {
                    "candidate": "gemini",
                    "attempt_id": "gemini:coach-boundary-13:1:1",
                    "case_id": "coach-boundary-13",
                    "contract_valid": True,
                    "metrics": {"label_accuracy": 0.75, "evidence_accuracy": 1.0},
                    "raw_output": {"intent_assessment": {"label": "aligned"}},
                    "labels": {"intent": "aligned"},
                },
                {
                    "candidate": "gemini",
                    "attempt_id": "gemini:coach-normal-01:1:1",
                    "case_id": "coach-normal-01",
                    "contract_valid": True,
                    "metrics": {"label_accuracy": 1.0, "evidence_accuracy": 1.0},
                },
                {
                    "candidate": "gemini",
                    "attempt_id": "gemini:coach-failure-26:1:1",
                    "case_id": "coach-failure-26",
                    "contract_valid": False,
                    "metrics": {"label_accuracy": None, "evidence_accuracy": None},
                },
                {
                    "candidate": "baseline",
                    "attempt_id": "baseline:coach-boundary-13:1:1",
                    "case_id": "coach-boundary-13",
                    "contract_valid": True,
                    "metrics": {"label_accuracy": 0.0, "evidence_accuracy": 0.0},
                },
            ]
        }

        review_template, markdown = build_review_pack(report, candidate="gemini")

        self.assertEqual(list(review_template), ["gemini:coach-boundary-13:1:1"])
        self.assertEqual(review_template["gemini:coach-boundary-13:1:1"]["scores"], {})
        self.assertIn("coach-boundary-13", markdown)
        self.assertNotIn("coach-normal-01", markdown)
        self.assertNotIn("coach-failure-26", markdown)

    def test_rejects_missing_candidate(self):
        with self.assertRaisesRegex(ValueError, "candidate"):
            build_review_pack({"attempts": []}, candidate="gemini")


if __name__ == "__main__":
    unittest.main()
