import unittest

from backend.tests.d6_evidence_utils import build_redacted_evidence


class D6EvidenceRedactionTest(unittest.TestCase):
    def test_evidence_keeps_execution_metadata_but_drops_sensitive_fields(self):
        result = build_redacted_evidence(
            case_id="d6-normal-01",
            http_status=200,
            called_tools=["get_question", "get_practice_attempt"],
            trace_id="trace-123",
            terminal_status="ok",
            answer_text="민감한 답변",
            source_url="https://private.example/job",
        )

        self.assertEqual(result["case_id"], "d6-normal-01")
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["mcp_tools"], ["get_practice_attempt", "get_question"])
        self.assertEqual(result["trace_id"], "trace-123")
        self.assertNotIn("answer_text", result)
        self.assertNotIn("source_url", result)


if __name__ == "__main__":
    unittest.main()
