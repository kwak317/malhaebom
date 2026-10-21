import json
import unittest
from pathlib import Path


CASES_PATH = Path(__file__).with_name("d6_evidence_cases.json")


def load_cases() -> list[dict[str, object]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


class D6EvidenceCasesTest(unittest.TestCase):
    def test_d6_cases_have_four_required_classes(self):
        cases = load_cases()

        self.assertEqual(
            {case["kind"] for case in cases},
            {"normal", "boundary", "injection", "failure"},
        )
        self.assertEqual(len(cases), 4)
        self.assertTrue(all(case["case_id"] for case in cases))
        self.assertTrue(all(case["answer_revision_id"] for case in cases))

    def test_cases_contain_only_synthetic_ids_and_external_expectations(self):
        for case in load_cases():
            self.assertTrue(str(case["case_id"]).startswith("d6-"))
            self.assertTrue(str(case["answer_revision_id"]).startswith("d6-"))
            self.assertIn("expected_http_status", case)
            self.assertIn("expected_terminal_statuses", case)
            self.assertTrue(case["expected_terminal_statuses"])
            self.assertNotIn("answer_text", case)
            self.assertNotIn("source_text", case)

    def test_normal_case_allows_evidence_driven_follow_up(self):
        normal = next(case for case in load_cases() if case["kind"] == "normal")
        self.assertEqual(
            set(normal["expected_terminal_statuses"]),
            {"ok", "needs_more_info"},
        )


if __name__ == "__main__":
    unittest.main()
