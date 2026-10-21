from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from evals.coaching_dataset import load_dataset  # noqa: E402


class PresentationCauseReasoningDatasetTest(unittest.TestCase):
    def test_case_activates_split_cause_criteria_with_human_defined_partial_labels(self):
        cases = load_dataset(
            PROJECT_ROOT / "evals" / "presentation_cause_reasoning.jsonl"
        )

        self.assertEqual([case.id for case in cases], ["presentation-cause-01"])
        case = cases[0]
        self.assertEqual(
            case.context.active_criterion_ids,
            [
                "problem_context",
                "cause_observation",
                "cause_inference",
                "own_action",
                "result_verification",
            ],
        )
        self.assertEqual(
            case.expected.criterion_assessments["cause_observation"].value,
            "partial",
        )
        self.assertEqual(
            case.expected.criterion_assessments["cause_inference"].value,
            "partial",
        )


if __name__ == "__main__":
    unittest.main()
