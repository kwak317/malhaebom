"""Regression tests for the redacted D9 MCP failure verifier."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_d9_mcp_failure.py")
SPEC = importlib.util.spec_from_file_location("verify_d9_mcp_failure", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFIER
SPEC.loader.exec_module(VERIFIER)


class D9McpFailureVerifierTest(unittest.TestCase):
    def test_expected_failure_is_reduced_to_safe_evidence(self) -> None:
        evidence = VERIFIER.build_evidence(
            status=503,
            payload={
                "detail": {
                    "state": "mcp_error",
                    "code": "COACHING_MCP_UNAVAILABLE",
                    "retryable": True,
                    "message": "MCP 내부 경로와 access token은 노출하면 안 됩니다.",
                }
            },
            trace_id="trace-123",
        )

        self.assertEqual(
            evidence,
            {
                "case_id": "d9-mcp-failure-01",
                "http_status": 503,
                "failure_state": "mcp_error",
                "error_code": "COACHING_MCP_UNAVAILABLE",
                "retryable": True,
                "trace_id_present": True,
                "user_message_present": True,
            },
        )
        self.assertNotIn("access token", str(evidence))

    def test_unexpected_success_is_rejected(self) -> None:
        evidence = VERIFIER.build_evidence(
            status=200,
            payload={"status": "needs_more_info"},
            trace_id="trace-123",
        )

        with self.assertRaisesRegex(SystemExit, "expected HTTP 503"):
            VERIFIER.assert_expected_failure(evidence)

    def test_wrong_mcp_error_is_rejected(self) -> None:
        evidence = VERIFIER.build_evidence(
            status=503,
            payload={
                "detail": {
                    "state": "provider_error",
                    "code": "COACHING_PROVIDER_UNAVAILABLE",
                    "retryable": True,
                    "message": "safe message",
                }
            },
            trace_id=None,
        )

        with self.assertRaisesRegex(SystemExit, "mcp_error"):
            VERIFIER.assert_expected_failure(evidence)


if __name__ == "__main__":
    unittest.main()
