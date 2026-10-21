import unittest
from unittest.mock import patch
from uuid import UUID

from backend.tests.run_d6_live_agent_e2e import (
    build_request,
    case_id_from_env,
    expected_result_for_case,
    is_expected_result,
    main,
    redact_result,
)


class D6LiveAgentE2ETest(unittest.TestCase):
    def test_build_request_uses_real_context_ids(self):
        request = build_request(
            question_id="preset-04",
            answer_revision_id="70000000-0000-4000-8000-000000000001",
            job_snapshot_id="80000000-0000-4000-8000-000000000001",
        )

        self.assertEqual(request["action"], "analyze")
        self.assertEqual(request["question_id"], "preset-04")
        self.assertEqual(
            UUID(request["answer_revision_id"]).version,
            4,
        )

    def test_redact_result_keeps_only_execution_metadata(self):
        result = redact_result(
            case_id="d6-normal-live-01",
            http_status=200,
            body={"status": "ok", "evidence": [{"quote": "secret"}]},
            trace_id="trace-1",
        )

        self.assertEqual(result, {
            "case_id": "d6-normal-live-01",
            "http_status": 200,
            "terminal_status": "ok",
            "trace_id": "trace-1",
        })
        self.assertNotIn("evidence", result)

    def test_normal_case_accepts_evidence_driven_needs_more_info(self):
        expected_http_status, expected_terminal_statuses = expected_result_for_case(
            "d6-normal-live-01"
        )
        self.assertEqual(expected_http_status, 200)
        self.assertEqual(set(expected_terminal_statuses), {"ok", "needs_more_info"})
        self.assertTrue(
            is_expected_result(
                200,
                {"status": "needs_more_info"},
                expected_http_status=expected_http_status,
                expected_terminal_statuses=expected_terminal_statuses,
            )
        )

    def test_normal_case_rejects_unexpected_terminal_status(self):
        expected_http_status, expected_terminal_statuses = expected_result_for_case(
            "d6-normal-live-01"
        )
        self.assertFalse(
            is_expected_result(
                200,
                {"status": "unsupported"},
                expected_http_status=expected_http_status,
                expected_terminal_statuses=expected_terminal_statuses,
            )
        )

    def test_main_accepts_normal_needs_more_info_by_case_policy(self):
        env = {
            "D6_API_BASE_URL": "http://localhost:8000",
            "D6_ACCESS_TOKEN": "raw-test-token",
            "D6_CASE_ID": "d6-normal-live-01",
            "D6_QUESTION_ID": "preset-04",
            "D6_ANSWER_REVISION_ID": "70000000-0000-4000-8000-000000000001",
            "D6_JOB_SNAPSHOT_ID": "80000000-0000-4000-8000-000000000001",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "backend.tests.run_d6_live_agent_e2e.post_agent",
                return_value=(200, {"status": "needs_more_info"}, "trace-1"),
            ),
            patch("builtins.print"),
        ):
            self.assertEqual(main(), 0)

    def test_main_rejects_normal_unexpected_terminal_status(self):
        env = {
            "D6_API_BASE_URL": "http://localhost:8000",
            "D6_ACCESS_TOKEN": "raw-test-token",
            "D6_CASE_ID": "d6-normal-live-01",
            "D6_QUESTION_ID": "preset-04",
            "D6_ANSWER_REVISION_ID": "70000000-0000-4000-8000-000000000001",
            "D6_JOB_SNAPSHOT_ID": "80000000-0000-4000-8000-000000000001",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch(
                "backend.tests.run_d6_live_agent_e2e.post_agent",
                return_value=(200, {"status": "unsupported"}, "trace-2"),
            ),
            patch("builtins.print"),
        ):
            self.assertEqual(main(), 1)

    def test_case_id_defaults_to_normal_live_case(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(case_id_from_env(), "d6-normal-live-01")

    def test_case_id_can_be_selected_for_live_evidence(self):
        with patch.dict(
            "os.environ",
            {"D6_CASE_ID": "d6-boundary-live-01"},
            clear=True,
        ):
            self.assertEqual(case_id_from_env(), "d6-boundary-live-01")


if __name__ == "__main__":
    unittest.main()
