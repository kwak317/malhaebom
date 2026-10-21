from __future__ import annotations

import asyncio
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.schemas.coaching import CoachingAnalyzeRequest  # noqa: E402
from app.core.auth import InvalidAccessToken  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.coaching_context import (  # noqa: E402
    DEMO_ANSWER_REVISION_ID,
    DEMO_JOB_SNAPSHOT_ID,
    DEMO_QUESTION_ID,
    CoachingContextNotFound,
    build_demo_coaching_service,
)
from app.services.attempt_comparison import (  # noqa: E402
    DEMO_CURRENT_COACHING_RUN_ID,
    DEMO_PREVIOUS_COACHING_RUN_ID,
    AttemptComparisonNotFound,
    build_demo_attempt_comparison_service,
)
from app.services.mcp_access import (  # noqa: E402
    McpAccessDenied,
    McpAccessTokenCodec,
)
from mcp_server.server import (  # noqa: E402
    compare_attempts,
    configure_mcp_dependencies,
    get_job_context,
    get_practice_attempt,
    get_question,
    mcp,
)


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        if token == "owner-token":
            return "user-owner"
        if token == "other-token":
            return "user-other"
        raise InvalidAccessToken()


class McpToolsTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(UTC)
        self.codec = McpAccessTokenCodec("test-only-secret-with-at-least-32-characters")
        self.request = CoachingAnalyzeRequest(
            action="analyze",
            question_id=DEMO_QUESTION_ID,
            answer_revision_id=DEMO_ANSWER_REVISION_ID,
            job_snapshot_id=DEMO_JOB_SNAPSHOT_ID,
        )
        self.context_service = build_demo_coaching_service(
            "user-owner",
            now=self.now,
        ).context_service
        self.comparison_service = build_demo_attempt_comparison_service(
            "user-owner",
            now=self.now,
        )
        configure_mcp_dependencies(
            context_service=self.context_service,
            comparison_service=self.comparison_service,
            token_codec=self.codec,
        )
        self.token = self.codec.issue(
            user_id="user-owner",
            request=self.request,
            now=self.now,
        )
        self.comparison_token = self.codec.issue_comparison(
            user_id="user-owner",
            previous_coaching_run_id=DEMO_PREVIOUS_COACHING_RUN_ID,
            current_coaching_run_id=DEMO_CURRENT_COACHING_RUN_ID,
            now=self.now,
        )

    def tearDown(self):
        configure_mcp_dependencies(context_service=None, token_codec=None)

    def test_registers_four_read_only_context_tools(self):
        tools = asyncio.run(mcp.list_tools())

        self.assertEqual(
            {tool.name for tool in tools},
            {
                "get_question",
                "get_practice_attempt",
                "get_job_context",
                "compare_attempts",
            },
        )

    def test_reads_question_attempt_and_job_context(self):
        question = get_question(self.token, DEMO_QUESTION_ID)
        attempt = get_practice_attempt(
            self.token,
            str(DEMO_ANSWER_REVISION_ID),
        )
        job_context = get_job_context(
            self.token,
            str(DEMO_JOB_SNAPSHOT_ID),
        )

        self.assertEqual(question["question_type"], "problem_solving")
        self.assertEqual(len(attempt["answer_segments"]), 2)
        self.assertNotIn("user_id", attempt)
        self.assertEqual(job_context["requirements"][0]["requirement_id"], "J01-R1")
        self.assertNotIn("user_id", job_context)

    def test_compares_only_run_pair_allowed_by_capability_token(self):
        result = compare_attempts(
            self.comparison_token,
            str(DEMO_PREVIOUS_COACHING_RUN_ID),
            str(DEMO_CURRENT_COACHING_RUN_ID),
        )

        self.assertTrue(result["comparison"]["content_available"])
        self.assertEqual(
            result["comparison"]["added_explanations"][0]["criterion_id"],
            "result_verification",
        )
        with self.assertRaises(McpAccessDenied):
            compare_attempts(
                self.comparison_token,
                str(DEMO_CURRENT_COACHING_RUN_ID),
                str(DEMO_PREVIOUS_COACHING_RUN_ID),
            )

    def test_context_and_comparison_tokens_are_not_interchangeable(self):
        with self.assertRaises(McpAccessDenied):
            compare_attempts(
                self.token,
                str(DEMO_PREVIOUS_COACHING_RUN_ID),
                str(DEMO_CURRENT_COACHING_RUN_ID),
            )
        with self.assertRaises(McpAccessDenied):
            get_question(self.comparison_token, DEMO_QUESTION_ID)

    def test_rejects_id_outside_token_scope_before_lookup(self):
        with self.assertRaises(McpAccessDenied):
            get_question(self.token, "preset-05")

        with self.assertRaises(McpAccessDenied):
            get_practice_attempt(self.token, "not-a-uuid")

    def test_rejects_expired_internal_token(self):
        expired = self.codec.issue(
            user_id="user-owner",
            request=self.request,
            now=self.now - timedelta(minutes=10),
            ttl_seconds=60,
        )

        with self.assertRaises(McpAccessDenied):
            get_practice_attempt(expired, str(DEMO_ANSWER_REVISION_ID))

    def test_repository_still_checks_token_user_ownership(self):
        other_user_token = self.codec.issue(
            user_id="user-other",
            request=self.request,
            now=self.now,
        )

        with self.assertRaises(CoachingContextNotFound):
            get_job_context(other_user_token, str(DEMO_JOB_SNAPSHOT_ID))

        other_comparison_token = self.codec.issue_comparison(
            user_id="user-other",
            previous_coaching_run_id=DEMO_PREVIOUS_COACHING_RUN_ID,
            current_coaching_run_id=DEMO_CURRENT_COACHING_RUN_ID,
            now=self.now,
        )
        with self.assertRaises(AttemptComparisonNotFound):
            compare_attempts(
                other_comparison_token,
                str(DEMO_PREVIOUS_COACHING_RUN_ID),
                str(DEMO_CURRENT_COACHING_RUN_ID),
            )

    def test_streamable_http_mcp_lists_and_calls_four_tools(self):
        headers = {
            "Authorization": "Bearer owner-token",
            "Accept": "application/json, text/event-stream",
            "Mcp-Protocol-Version": "2025-06-18",
        }
        with TestClient(
            create_app(token_verifier=FakeVerifier()),
            base_url="http://localhost:8000",
        ) as client:
            initialize = client.post(
                "/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1"},
                    },
                },
            )
            listed = client.post(
                "/mcp",
                headers=headers,
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
            calls = [
                self._call_http_tool(
                    client,
                    headers,
                    3,
                    "get_question",
                    {"context_token": self.token, "question_id": DEMO_QUESTION_ID},
                ),
                self._call_http_tool(
                    client,
                    headers,
                    4,
                    "get_practice_attempt",
                    {
                        "context_token": self.token,
                        "answer_revision_id": str(DEMO_ANSWER_REVISION_ID),
                    },
                ),
                self._call_http_tool(
                    client,
                    headers,
                    5,
                    "get_job_context",
                    {
                        "context_token": self.token,
                        "job_snapshot_id": str(DEMO_JOB_SNAPSHOT_ID),
                    },
                ),
                self._call_http_tool(
                    client,
                    headers,
                    6,
                    "compare_attempts",
                    {
                        "context_token": self.comparison_token,
                        "previous_coaching_run_id": str(
                            DEMO_PREVIOUS_COACHING_RUN_ID
                        ),
                        "current_coaching_run_id": str(
                            DEMO_CURRENT_COACHING_RUN_ID
                        ),
                    },
                ),
            ]

        self.assertEqual(initialize.status_code, 200)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            {tool["name"] for tool in listed.json()["result"]["tools"]},
            {
                "get_question",
                "get_practice_attempt",
                "get_job_context",
                "compare_attempts",
            },
        )
        self.assertTrue(all(not response.json()["result"]["isError"] for response in calls))

    def test_streamable_http_mcp_requires_bearer_and_matching_user(self):
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_question",
                "arguments": {
                    "context_token": self.token,
                    "question_id": DEMO_QUESTION_ID,
                },
            },
        }
        base_headers = {
            "Accept": "application/json, text/event-stream",
            "Mcp-Protocol-Version": "2025-06-18",
        }
        with TestClient(
            create_app(token_verifier=FakeVerifier()),
            base_url="http://localhost:8000",
        ) as client:
            missing = client.post("/mcp", headers=base_headers, json=request)
            mismatched = client.post(
                "/mcp",
                headers={**base_headers, "Authorization": "Bearer other-token"},
                json=request,
            )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(mismatched.status_code, 200)
        self.assertTrue(mismatched.json()["result"]["isError"])

    def test_streamable_http_mcp_rejects_id_outside_capability_scope(self):
        owner_access_token = "-".join(("owner", "token"))
        headers = {
            "Authorization": " ".join(("Bearer", owner_access_token)),
            "Accept": "application/json, text/event-stream",
            "Mcp-Protocol-Version": "2025-06-18",
        }
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_question",
                "arguments": {
                    "context_token": self.token,
                    "question_id": "preset-05",
                },
            },
        }
        with TestClient(
            create_app(token_verifier=FakeVerifier()),
            base_url="http://localhost:8000",
        ) as client:
            response = client.post("/mcp", headers=headers, json=request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["result"]["isError"])

    def test_http_mcp_mount_does_not_shadow_health_check(self):
        with TestClient(
            create_app(token_verifier=FakeVerifier()),
            base_url="http://localhost:8000",
        ) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @staticmethod
    def _call_http_tool(client, headers, request_id, name, arguments):
        return client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )


if __name__ == "__main__":
    unittest.main()
