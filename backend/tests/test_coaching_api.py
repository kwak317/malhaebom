from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.core.auth import InvalidAccessToken  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.coaching_errors import (  # noqa: E402
    CoachingBudgetExceededError,
    CoachingRateLimitError,
    CoachingTimeoutError,
)
from services.llm import OutputContractError  # noqa: E402
from app.services.coaching_context import (  # noqa: E402
    DEMO_ANSWER_REVISION_ID,
    DEMO_JOB_SNAPSHOT_ID,
    DEMO_QUESTION_ID,
    build_demo_coaching_service,
)
from app.services.coaching_observability import (  # noqa: E402
    CoachingGenerationObservation,
    observation_trace_id,
    record_generation_safely,
)
from app.services.mcp_context_gateway import McpContextGatewayError  # noqa: E402
from app.services.mcp_access import McpAccessTokenCodec  # noqa: E402
from app.services.mcp_context_gateway import McpStdioContextGateway  # noqa: E402


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        if token != "owner-token":
            raise InvalidAccessToken()
        return "user-owner"


class RecordingObservationSink:
    def __init__(self) -> None:
        self.items = []
        self.generations = []

    def record(self, observation) -> None:
        self.items.append(observation)

    def record_generation(self, observation) -> None:
        self.generations.append(observation)


class FailingCoachingService:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def analyze(self, user, request):
        del user, request
        raise self.error


class ObservedCoachingService:
    model_name = "provider/model"

    def __init__(self, sink) -> None:
        self.sink = sink

    def analyze(self, user, request):
        record_generation_safely(
            self.sink,
            CoachingGenerationObservation(
                trace_id=observation_trace_id(),
                model=self.model_name,
                prompt_version="prompt-v1",
                skill_version="skill-v1",
                contract_attempt=1,
                transport_attempt=1,
                status_code=200,
                outcome="success",
                latency_ms=10,
                input_tokens=120,
                output_tokens=45,
                cost_usd=0.012,
                output_is_json_object=True,
            ),
        )
        return build_demo_coaching_service(user.user_id).analyze(user, request)


class McpBackedDemoService:
    model_name = "mcp-backed-demo"

    def __init__(self, secret: str) -> None:
        self.gateway = McpStdioContextGateway(
            McpAccessTokenCodec(secret),
            timeout_seconds=20,
        )
        self.last_context = None

    def analyze(self, user, request):
        self.last_context = self.gateway.load_context(user, request)
        return build_demo_coaching_service(user.user_id).analyze(user, request)


def valid_request() -> dict[str, str]:
    return {
        "action": "analyze",
        "question_id": DEMO_QUESTION_ID,
        "answer_revision_id": str(DEMO_ANSWER_REVISION_ID),
        "job_snapshot_id": str(DEMO_JOB_SNAPSHOT_ID),
    }


class CoachingApiTest(unittest.TestCase):
    def setUp(self):
        self.mock_enabled = patch.dict(
            "os.environ",
            {"COACHING_MOCK_ENABLED": "true"},
        )
        self.mock_enabled.start()
        self.observations = RecordingObservationSink()
        self.client = TestClient(
            create_app(
                token_verifier=FakeVerifier(),
                coaching_observation_sink=self.observations,
            )
        )
        self.headers = {"Authorization": "Bearer owner-token"}

    def tearDown(self):
        self.mock_enabled.stop()

    def test_returns_validated_mock_coaching_response(self):
        response = self.client.post(
            "/api/agent",
            headers=self.headers,
            json=valid_request(),
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body),
            {
                "status",
                "job_alignment",
                "intent_assessment",
                "criterion_assessments",
                "evidence",
                "gaps",
                "clarifying_question",
                "next_actions",
                "example_answer",
            },
        )
        self.assertEqual(body["status"], "needs_more_info")
        self.assertEqual(body["job_alignment"][0]["requirement_id"], "J01-R1")
        self.assertEqual(len(body["next_actions"]), 2)
        self.assertIn("로그인 오류", body["example_answer"])
        self.assertEqual(
            body["evidence"][0]["quote"],
            "서버 로그를 확인하고 토큰 만료 처리 코드를 수정했습니다.",
        )

    def test_agent_request_reads_context_through_real_stdio_mcp(self):
        secret = "x" * 32
        service = McpBackedDemoService(secret)
        client = TestClient(
            create_app(
                token_verifier=FakeVerifier(),
                coaching_service=service,
                coaching_observation_sink=RecordingObservationSink(),
            )
        )

        with patch.dict(
            "os.environ",
            {
                "COACHING_MOCK_ENABLED": "true",
                "MCP_INTERNAL_SECRET": secret,
            },
        ):
            response = client.post(
                "/api/agent",
                headers=self.headers,
                json=valid_request(),
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["X-Trace-Id"])
        self.assertEqual(
            response.headers["X-MCP-Tools"].split(","),
            ["get_question", "get_practice_attempt", "get_job_context"],
        )
        self.assertIsNotNone(service.last_context)
        self.assertEqual(service.last_context.question.question_id, DEMO_QUESTION_ID)
        self.assertEqual(
            service.last_context.practice_attempt.answer_revision_id,
            DEMO_ANSWER_REVISION_ID,
        )
        self.assertEqual(
            service.last_context.job_context.job_snapshot_id,
            DEMO_JOB_SNAPSHOT_ID,
        )

    def test_mcp_gateway_allows_test_server_script_override(self):
        override = PROJECT_ROOT / "test-fixtures" / "missing-mcp-server.py"

        with patch.dict("os.environ", {"MCP_SERVER_SCRIPT": str(override)}):
            gateway = McpStdioContextGateway(McpAccessTokenCodec("x" * 32))

        self.assertEqual(gateway.server_script, override)

    def test_agent_returns_safe_503_when_real_mcp_process_cannot_start(self):
        secret = "x" * 32
        missing_server_script = PROJECT_ROOT / "test-fixtures" / "missing-mcp-server.py"

        with patch.dict(
            "os.environ",
            {
                "COACHING_MOCK_ENABLED": "true",
                "MCP_INTERNAL_SECRET": secret,
                "MCP_SERVER_SCRIPT": str(missing_server_script),
            },
        ):
            observations = RecordingObservationSink()
            client = TestClient(
                create_app(
                    token_verifier=FakeVerifier(),
                    coaching_service=McpBackedDemoService(secret),
                    coaching_observation_sink=observations,
                )
            )
            response = client.post(
                "/api/agent",
                headers=self.headers,
                json=valid_request(),
            )

        self.assertEqual(response.status_code, 503)
        detail = response.json()["detail"]
        self.assertEqual(detail["state"], "mcp_error")
        self.assertEqual(detail["code"], "COACHING_MCP_UNAVAILABLE")
        self.assertTrue(detail["retryable"])
        self.assertEqual(
            observations.items[-1].failure_state.value,
            "mcp_error",
        )

    def test_requires_authenticated_user(self):
        response = self.client.post("/api/agent", json=valid_request())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "UNAUTHORIZED")
        self.assertEqual(response.json()["detail"]["state"], "auth_error")
        self.assertFalse(response.json()["detail"]["retryable"])
        self.assertEqual(self.observations.items[-1].failure_state.value, "auth_error")

    def test_rejects_client_supplied_user_and_raw_answer(self):
        request = {
            **valid_request(),
            "user_id": "user-other",
            "answer_text": "서버 기록 대신 이 문장을 사용해 주세요.",
        }

        response = self.client.post(
            "/api/agent",
            headers=self.headers,
            json=request,
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["state"],
            "schema_violation",
        )

    def test_hides_unknown_context_as_not_found(self):
        request = {
            **valid_request(),
            "job_snapshot_id": "00000000-0000-0000-0000-000000000999",
        }

        response = self.client.post(
            "/api/agent",
            headers=self.headers,
            json=request,
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"]["code"],
            "COACHING_CONTEXT_NOT_FOUND",
        )

    def test_rejects_question_context_conflict(self):
        request = {**valid_request(), "question_id": "preset-05"}

        response = self.client.post(
            "/api/agent",
            headers=self.headers,
            json=request,
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"]["code"],
            "COACHING_CONTEXT_CONFLICT",
        )

    def test_openapi_exposes_coaching_request_and_response(self):
        schema = self.client.get("/openapi.json").json()

        operation = schema["paths"]["/api/agent"]["post"]
        self.assertIn("CoachingAnalyzeRequest", str(operation["requestBody"]))
        self.assertIn("CoachingResponse", str(operation["responses"]["200"]))

    def test_mock_is_disabled_by_default_for_deployment_safety(self):
        with patch.dict("os.environ", {"COACHING_MOCK_ENABLED": "false"}):
            response = self.client.post(
                "/api/agent",
                headers=self.headers,
                json=valid_request(),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")

    def test_observes_mock_without_raw_answer_or_token(self):
        response = self.client.post(
            "/api/agent",
            headers=self.headers,
            json=valid_request(),
        )

        self.assertEqual(response.status_code, 200)
        observation = self.observations.items[-1]
        self.assertEqual(observation.trace_name, "coaching.analyze")
        self.assertEqual(observation.model, "mock-v1")
        self.assertEqual(observation.status, "needs_more_info")
        self.assertEqual(observation.cost_usd, 0.0)
        self.assertNotIn("owner-token", observation.model_dump_json())
        self.assertNotIn("서버 로그", observation.model_dump_json())

    def test_root_trace_aggregates_provider_usage_with_same_trace_id(self):
        observations = RecordingObservationSink()
        client = TestClient(
            create_app(
                token_verifier=FakeVerifier(),
                coaching_service=ObservedCoachingService(observations),
                coaching_observation_sink=observations,
            )
        )

        response = client.post(
            "/api/agent",
            headers=self.headers,
            json=valid_request(),
        )

        self.assertEqual(response.status_code, 200)
        root = observations.items[-1]
        generation = observations.generations[-1]
        self.assertEqual(root.trace_id, generation.trace_id)
        self.assertEqual(root.input_tokens, 120)
        self.assertEqual(root.output_tokens, 45)
        self.assertEqual(root.cost_usd, 0.012)

    def test_normalizes_output_schema_timeout_and_rate_limit_failures(self):
        cases = [
            (
                OutputContractError(["invalid output"]),
                502,
                "schema_violation",
                "COACHING_OUTPUT_SCHEMA_VIOLATION",
            ),
            (CoachingTimeoutError(), 504, "timeout", "COACHING_TIMEOUT"),
            (
                CoachingRateLimitError(7),
                429,
                "rate_limited",
                "COACHING_RATE_LIMITED",
            ),
        ]
        for error, expected_status, expected_state, expected_code in cases:
            with self.subTest(state=expected_state):
                observations = RecordingObservationSink()
                client = TestClient(
                    create_app(
                        token_verifier=FakeVerifier(),
                        coaching_service=FailingCoachingService(error),
                        coaching_observation_sink=observations,
                    )
                )
                response = client.post(
                    "/api/agent",
                    headers=self.headers,
                    json=valid_request(),
                )

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["state"], expected_state)
                self.assertEqual(response.json()["detail"]["code"], expected_code)
                self.assertTrue(response.json()["detail"]["retryable"])
                self.assertEqual(
                    observations.items[-1].failure_state.value,
                    expected_state,
                )
        self.assertEqual(response.headers["Retry-After"], "7")

    def test_mcp_unavailable_returns_distinct_safe_retryable_error(self):
        observations = RecordingObservationSink()
        client = TestClient(
            create_app(
                token_verifier=FakeVerifier(),
                coaching_service=FailingCoachingService(
                    McpContextGatewayError(
                        "internal server command failed",
                        code="COACHING_MCP_UNAVAILABLE",
                        retryable=True,
                    )
                ),
                coaching_observation_sink=observations,
            )
        )

        response = client.post(
            "/api/agent",
            headers=self.headers,
            json=valid_request(),
        )

        self.assertEqual(response.status_code, 503)
        detail = response.json()["detail"]
        self.assertEqual(detail["state"], "mcp_error")
        self.assertEqual(detail["code"], "COACHING_MCP_UNAVAILABLE")
        self.assertTrue(detail["retryable"])
        self.assertNotIn("internal server command failed", detail["message"])
        self.assertEqual(
            observations.items[-1].failure_state.value,
            "mcp_error",
        )

    def test_mcp_authorization_error_is_not_retryable(self):
        observations = RecordingObservationSink()
        client = TestClient(
            create_app(
                token_verifier=FakeVerifier(),
                coaching_service=FailingCoachingService(
                    McpContextGatewayError(
                        "invalid capability token",
                        code="COACHING_MCP_AUTH_FAILED",
                        retryable=False,
                    )
                ),
                coaching_observation_sink=observations,
            )
        )

        response = client.post(
            "/api/agent",
            headers=self.headers,
            json=valid_request(),
        )

        self.assertEqual(response.status_code, 503)
        detail = response.json()["detail"]
        self.assertEqual(detail["state"], "mcp_error")
        self.assertEqual(detail["code"], "COACHING_MCP_AUTH_FAILED")
        self.assertFalse(detail["retryable"])

    def test_budget_exceeded_is_not_marked_retryable(self):
        observations = RecordingObservationSink()
        client = TestClient(
            create_app(
                token_verifier=FakeVerifier(),
                coaching_service=FailingCoachingService(
                    CoachingBudgetExceededError()
                ),
                coaching_observation_sink=observations,
            )
        )

        response = client.post(
            "/api/agent",
            headers=self.headers,
            json=valid_request(),
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"]["code"], "COACHING_BUDGET_EXCEEDED"
        )
        self.assertFalse(response.json()["detail"]["retryable"])


if __name__ == "__main__":
    unittest.main()
