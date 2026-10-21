from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for entry in (ROOT, BACKEND):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from evals.coaching_dataset import load_dataset  # noqa: E402
from evals.run_service_candidate_integration import (  # noqa: E402
    DEFAULT_CASE_IDS,
    MODELS,
    build_context,
    summarize,
)


class ServiceCandidateIntegrationTest(unittest.TestCase):
    def test_representative_cases_build_real_service_contexts(self):
        cases = {
            case.id: case for case in load_dataset(ROOT / "evals/dataset.v2.jsonl")
        }

        self.assertEqual(
            [cases[case_id].category for case_id in DEFAULT_CASE_IDS],
            ["normal", "boundary", "failure"],
        )
        for case_id in DEFAULT_CASE_IDS:
            context = build_context(cases[case_id])
            validation = context.to_validation_context()
            self.assertEqual(validation, cases[case_id].context)
            self.assertEqual(context.question.question_id, "preset-04")

    def test_summary_counts_retries_repairs_and_unknown_costs(self):
        records = []
        for model in MODELS:
            records.append(
                {
                    "model": model,
                    "http_status": 200,
                    "contract_valid": True,
                    "validator_passed": True,
                    "elapsed_ms": 10.0,
                    "generation_attempts": [
                        {"cost_usd": 0.01, "will_retry": True},
                        {"cost_usd": None, "will_retry": False},
                    ],
                    "validation_attempts": [{"valid": False}, {"valid": True}],
                }
            )

        summaries = summarize(records)

        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0]["transport_retries"], 1)
        self.assertEqual(summaries[0]["contract_repairs"], 1)
        self.assertEqual(summaries[0]["unknown_cost_attempts"], 1)
        self.assertEqual(summaries[0]["known_cost_usd"], 0.01)


if __name__ == "__main__":
    unittest.main()
