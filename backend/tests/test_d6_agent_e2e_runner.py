from __future__ import annotations

import io
import json
import unittest
import urllib.error
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from backend.tests.run_d6_agent_e2e import (
    detect_api_base_url,
    list_job_candidates,
    load_case_inputs,
    main,
    normalize_access_token,
    request_json,
    resolve_access_token,
    run_case,
    select_job_candidate,
)

ANALYSIS_JOB_ID = "30000000-0000-4000-8000-000000000001"
JWT = "header.payload.signature"
REVISION = {
    "question_id": "preset-04",
    "answer_revision_id": "40000000-0000-4000-8000-000000000001",
    "job_snapshot_id": "60000000-0000-4000-8000-000000000001",
}
RECORDS = {
    "records": [{
        "practice_session_id": "session-1",
        "question_id": "preset-04",
        "practiced_at": "2026-09-29T08:00:00Z",
        "attempts": [{
            "attempt_no": 1,
            "job_id": ANALYSIS_JOB_ID,
            "transcript": "private",
            "feedback": ["private"],
        }],
    }]
}


class D6AgentE2ERunnerTest(unittest.TestCase):
    def test_api_url_detection_prefers_explicit_then_compose(self):
        with patch("backend.tests.run_d6_agent_e2e.subprocess.run") as run:
            self.assertEqual(
                detect_api_base_url("http://localhost:19000/"),
                "http://localhost:19000",
            )
            run.assert_not_called()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "backend.tests.run_d6_agent_e2e.subprocess.run",
                return_value=SimpleNamespace(
                    returncode=0, stdout="0.0.0.0:18000\n", stderr=""
                ),
            ),
        ):
            self.assertEqual(detect_api_base_url(), "http://localhost:18000")

    def test_token_normalization_and_hidden_prompt(self):
        self.assertEqual(
            normalize_access_token(f"Authorization: Bearer {JWT}"), JWT
        )
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("backend.tests.run_d6_agent_e2e.sys.stdin.isatty", return_value=True),
            patch(
                "backend.tests.run_d6_agent_e2e.getpass.getpass",
                return_value=f"Bearer {JWT}",
            ),
        ):
            self.assertEqual(resolve_access_token(), JWT)

    def test_network_failure_is_redacted(self):
        with patch(
            "backend.tests.run_d6_agent_e2e.urllib.request.urlopen",
            side_effect=urllib.error.URLError("timeout"),
        ):
            status, body, trace_id = request_json(
                base_url="http://localhost:18000",
                token=JWT,
                method="GET",
                path="/health",
                timeout=1,
            )
        self.assertEqual((status, body, trace_id), (
            0, {"status": "network_error"}, None
        ))

    def test_inputs_and_job_candidates_are_safe(self):
        cases = load_case_inputs()
        self.assertEqual(
            [case["kind"] for case in cases],
            ["normal", "boundary", "injection"],
        )
        candidates = list_job_candidates(RECORDS)
        self.assertEqual(candidates[0]["analysis_job_id"], ANALYSIS_JOB_ID)
        self.assertNotIn("transcript", candidates[0])
        self.assertNotIn("feedback", candidates[0])

        with redirect_stdout(io.StringIO()):
            selected = select_job_candidate(candidates, input_fn=lambda _: "1")
        self.assertEqual(selected, ANALYSIS_JOB_ID)

    def test_run_case_applies_policy_and_redacts_context(self):
        normal = {
            "case_id": "d6-normal-live-auto-01",
            "kind": "normal",
            "confirmed_text": "synthetic normal answer",
        }
        with patch(
            "backend.tests.run_d6_agent_e2e.request_json",
            side_effect=[
                (201, REVISION, None),
                (200, {"status": "needs_more_info"}, "trace-normal"),
            ],
        ):
            result = run_case(
                base_url="http://localhost:8000",
                token=JWT,
                analysis_job_id=ANALYSIS_JOB_ID,
                case=normal,
            )
        self.assertTrue(result["passed"])
        self.assertEqual(result["terminal_status"], "needs_more_info")
        self.assertNotIn("confirmed_text", result)
        self.assertNotIn("answer_revision_id", result)
        self.assertNotIn("job_snapshot_id", result)

        boundary = {
            "case_id": "d6-boundary-live-auto-01",
            "kind": "boundary",
            "confirmed_text": "synthetic boundary answer",
        }
        with patch(
            "backend.tests.run_d6_agent_e2e.request_json",
            side_effect=[
                (201, REVISION, None),
                (200, {"status": "ok"}, "trace-boundary"),
            ],
        ):
            rejected = run_case(
                base_url="http://localhost:8000",
                token=JWT,
                analysis_job_id=ANALYSIS_JOB_ID,
                case=boundary,
            )
        self.assertFalse(rejected["passed"])

    def test_list_jobs_401_is_auth_failure_not_empty_success(self):
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"D6_ACCESS_TOKEN": JWT}, clear=True),
            patch(
                "backend.tests.run_d6_agent_e2e.request_json",
                side_effect=[
                    (200, {"status": "ok"}, None),
                    (401, {"detail": "Unauthorized"}, None),
                ],
            ),
            redirect_stdout(output),
        ):
            exit_code = main([
                "--list-jobs",
                "--api-base-url",
                "http://localhost:18000",
            ])
        parsed = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(parsed["http_status"], 401)
        self.assertIn("unauthorized", parsed["error"])

    def test_interactive_flow_selects_job_and_runs_all_cases(self):
        cases = load_case_inputs()
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"D6_ACCESS_TOKEN": JWT}, clear=True),
            patch(
                "backend.tests.run_d6_agent_e2e.request_json",
                side_effect=[
                    (200, {"status": "ok"}, None),
                    (200, RECORDS, None),
                ],
            ),
            patch("backend.tests.run_d6_agent_e2e.sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value="1"),
            patch(
                "backend.tests.run_d6_agent_e2e.run_case",
                side_effect=[
                    {"case_id": case["case_id"], "stage": "agent", "passed": True}
                    for case in cases
                ],
            ) as run_case_mock,
            redirect_stdout(output),
        ):
            exit_code = main(["--api-base-url", "http://localhost:18000"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_case_mock.call_count, 3)
        self.assertTrue(all(
            call.kwargs["analysis_job_id"] == ANALYSIS_JOB_ID
            for call in run_case_mock.call_args_list
        ))
        json_lines = [
            json.loads(line)
            for line in output.getvalue().splitlines()
            if line.startswith("{")
        ]
        self.assertEqual(
            json_lines[-1], {"summary": {"passed": 3, "total": 3}}
        )


if __name__ == "__main__":
    unittest.main()
