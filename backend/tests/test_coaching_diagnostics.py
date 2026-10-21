from __future__ import annotations

import json
import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
for path in (BACKEND_ROOT, BACKEND_ROOT.parent):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.main import create_app  # noqa: E402
from app.services.coaching_diagnostics import CoachingAttemptFailure  # noqa: E402
from app.services.coaching_observability import LangfuseCoachingObservationSink  # noqa: E402
from app.services.coaching_runtime import McpLlmCoachingService, OpenAICompatibleJsonProvider  # noqa: E402
from app.services.mcp_context_gateway import McpContextGatewayError  # noqa: E402
from app.services.supabase_coaching_runs import CoachingRunPersistenceError  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from tests.test_coaching_api import FakeVerifier, RecordingObservationSink  # noqa: E402
from tests.test_coaching_runtime import (  # noqa: E402
    FakeGateway, FakeProvider, REVISION_ID, JOB_ID, context_bundle, valid_output,
)


LOGGER = "app.services.coaching_diagnostics"
HEADERS = {"Authorization": "Bearer owner-token"}
REQUEST = {
    "action": "analyze", "question_id": "preset-04",
    "answer_revision_id": str(REVISION_ID), "job_snapshot_id": str(JOB_ID),
}


class RecordingHttp(httpx.Client):
    def __init__(self):
        self.last_request = None
        self.calls = 0
        self.status_code = 200
        self.response_headers = {}
        self.response_body = {
            "id": "test-completion",
            "object": "chat.completion",
            "created": 0,
            "model": "provider/model",
            "choices": [{
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(valid_output())},
            }],
        }
        self.transport_error = None
        super().__init__(transport=httpx.MockTransport(self.handle))

    def handle(self, request):
        self.calls += 1
        self.last_request = {
            "url": str(request.url),
            "json": json.loads(request.content),
            "headers": dict(request.headers),
            "timeout": request.extensions["timeout"],
        }
        if self.transport_error is not None:
            raise self.transport_error("test transport failure", request=request)
        return httpx.Response(
            self.status_code, headers=self.response_headers, json=self.response_body
        )


class CoachingDiagnosticsTest(unittest.TestCase):
    def client(self, provider, *, gateway=None, repository=None, sink=None, max_attempts=2):
        self.observations = sink if sink is not None else RecordingObservationSink()
        return TestClient(create_app(
            token_verifier=FakeVerifier(),
            coaching_service=McpLlmCoachingService(
                gateway or FakeGateway(), provider, run_repository=repository, max_attempts=max_attempts,
            ),
            coaching_observation_sink=self.observations,
        ))

    def test_observation_records_actual_service_versions_not_stale_env(self):
        provider = FakeProvider([valid_output()])
        provider.prompt_version = "malhaebom-coaching@7"
        provider.skill_version = "interview-coach-test-active"
        with patch.dict(os.environ, {
            "COACHING_PROMPT_VERSION": "stale-local-prompt",
            "COACHING_SKILL_VERSION": "stale-local-skill",
        }):
            response = self.client(provider).post(
                "/api/agent", headers=HEADERS, json=REQUEST,
            )
        self.assertEqual(response.status_code, 200)
        observation = self.observations.items[-1]
        self.assertEqual(observation.prompt_version, provider.prompt_version)
        self.assertEqual(observation.skill_version, provider.skill_version)

    def test_parse_failures_have_specific_code_with_one_configured_attempt(self):
        for content, code in [
            ("private-answer-not-json", "COACHING_JSON_PARSE_FAILED"),
            ("[]", "COACHING_JSON_OBJECT_REQUIRED"),
            (None, "COACHING_JSON_PARSE_FAILED"),
        ]:
            with self.subTest(code=code), RecordingHttp() as http:
                http.response_body["choices"][0]["message"]["content"] = content
                provider = OpenAICompatibleJsonProvider(
                    api_key="private-provider-key", model_name="provider/model",
                    base_url="https://provider.example/v1", http_client=http, max_transport_attempts=1,
                )
                with self.assertLogs(LOGGER) as logs:
                    response = self.client(provider, max_attempts=1).post("/api/agent", headers=HEADERS, json=REQUEST)
                observation = self.observations.items[-1]
                self.assertEqual(response.status_code, 502)
                self.assertEqual(http.calls, 1)
                self.assertEqual((observation.failure_stage, observation.error_code), ("parse", code))
                self.assertEqual(observation.model, "provider/model")
                self.assertEqual((observation.attempt_count, observation.retry_count), (1, 0))
                self.assertEqual(len(observation.attempt_failures), 1)
                self.assertIn(observation.trace_id, str(logs.output))
                for secret in ("private-answer", "private-provider-key", "owner-token"):
                    self.assertNotIn(secret, str(logs.output) + observation.model_dump_json())

    def test_parse_failure_is_preserved_when_latest_default_repair_succeeds(self):
        contents = ["private-invalid-json", json.dumps(valid_output())]

        def respond(request):
            return httpx.Response(200, json={"choices": [{"message": {"content": contents.pop(0)}}]})

        with httpx.Client(transport=httpx.MockTransport(respond)) as http:
            provider = OpenAICompatibleJsonProvider(
                api_key="private-key", model_name="provider/model",
                base_url="https://provider.example/v1", http_client=http, max_transport_attempts=1,
            )
            with self.assertLogs(LOGGER) as logs:
                response = self.client(provider).post("/api/agent", headers=HEADERS, json=REQUEST)
        observation = self.observations.items[-1]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contents, [])
        self.assertEqual((observation.attempt_count, observation.retry_count), (2, 1))
        self.assertIsNone(observation.failure_stage)
        self.assertIsNone(observation.error_code)
        self.assertEqual(len(observation.attempt_failures), 1)
        self.assertEqual(observation.attempt_failures[0].error_code, "COACHING_JSON_PARSE_FAILED")
        self.assertNotIn("private-invalid-json", str(logs.output) + observation.model_dump_json())

    def test_validation_failures_survive_repair_success_and_exhaustion(self):
        invalid = deepcopy(valid_output())
        invalid["criterion_assessments"][0]["evidence"][0]["quote"] = "private-invalid-quote"
        for final_output, expected_status in [(valid_output(), 200), (invalid, 502)]:
            with self.subTest(status=expected_status), self.assertLogs(LOGGER):
                provider = FakeProvider([invalid, final_output])
                response = self.client(provider).post("/api/agent", headers=HEADERS, json=REQUEST)
            observation = self.observations.items[-1]
            self.assertEqual(response.status_code, expected_status)
            self.assertEqual((observation.attempt_count, observation.retry_count), (2, 1))
            self.assertEqual(len(observation.attempt_failures), 1 if expected_status == 200 else 2)
            self.assertEqual(observation.attempt_failures[0].stage, "validation")
            self.assertEqual(observation.attempt_failures[0].error_code, "COACHING_OUTPUT_VALIDATION_FAILED")
            self.assertEqual(observation.failure_stage, None if expected_status == 200 else "validation")
            self.assertNotIn("private-invalid-quote", observation.model_dump_json())
            self.assertNotIn("attempt_failures", response.json())

    def test_context_and_persistence_failures_identify_stage_and_calls(self):
        class FailingGateway:
            def load_context(self, *args):
                raise McpContextGatewayError("private-context-token")

        class FailingRepository:
            def save(self, *args, **kwargs):
                raise CoachingRunPersistenceError("private-database-token")

        for gateway, repository, stage, calls, code in [
            (FailingGateway(), None, "context", 0, "COACHING_CONTEXT_LOAD_FAILED"),
            (None, FailingRepository(), "persistence", 1, "COACHING_RESULT_SAVE_FAILED"),
        ]:
            with self.subTest(stage=stage), self.assertLogs(LOGGER) as logs:
                provider = FakeProvider([valid_output()])
                response = self.client(provider, gateway=gateway, repository=repository).post(
                    "/api/agent", headers=HEADERS, json=REQUEST,
                )
            observation = self.observations.items[-1]
            self.assertEqual(response.status_code, 503)
            self.assertEqual((observation.failure_stage, observation.error_code), (stage, code))
            self.assertEqual(observation.attempt_count, calls)
            self.assertEqual(provider.calls, calls)
            self.assertEqual(observation.retry_count, 0)
            self.assertNotIn("private-", str(logs.output) + observation.model_dump_json())

    def test_provider_http_failures_are_distinct(self):
        for status, code, response_status in [
            (402, "COACHING_CREDITS_EXHAUSTED", 503),
            (429, "COACHING_RATE_LIMITED", 429),
            (503, "COACHING_PROVIDER_HTTP_ERROR", 503),
        ]:
            with self.subTest(status=status), RecordingHttp() as http, self.assertLogs(LOGGER):
                http.status_code = status
                provider = OpenAICompatibleJsonProvider(
                    api_key="private-key", model_name="provider/model",
                    base_url="https://provider.example/v1", http_client=http, max_transport_attempts=1,
                )
                response = self.client(provider).post("/api/agent", headers=HEADERS, json=REQUEST)
                observation = self.observations.items[-1]
                self.assertEqual(response.status_code, response_status)
                self.assertEqual((observation.failure_stage, observation.error_code), ("provider", code))
                self.assertEqual((observation.attempt_count, http.calls), (1, 1))

    def test_timeout_and_connection_failures_keep_provider_details(self):
        for error_type, code, status in [
            (httpx.ReadTimeout, "COACHING_TIMEOUT", 504),
            (httpx.ConnectError, "COACHING_PROVIDER_CONNECTION_FAILED", 503),
        ]:
            def fail(request):
                raise error_type("private-network-message", request=request)

            with self.subTest(code=code), httpx.Client(transport=httpx.MockTransport(fail)) as http:
                provider = OpenAICompatibleJsonProvider(
                    api_key="private-key", model_name="provider/model",
                    base_url="https://provider.example/v1", http_client=http, max_transport_attempts=1,
                )
                with self.assertLogs(LOGGER) as logs:
                    response = self.client(provider).post("/api/agent", headers=HEADERS, json=REQUEST)
                observation = self.observations.items[-1]
                self.assertEqual(response.status_code, status)
                self.assertEqual((observation.failure_stage, observation.error_code), ("provider", code))
                self.assertEqual((observation.attempt_count, observation.retry_count), (1, 0))
                self.assertNotIn("private-network-message", str(logs.output))

    def test_concurrent_requests_do_not_share_history(self):
        barrier = Barrier(2)
        failed_revision = str(REVISION_ID)
        successful_revision = "70000000-0000-4000-8000-000000000002"

        class ConcurrentGateway:
            def load_context(self, user, request):
                barrier.wait(timeout=5)
                context = context_bundle()
                context.practice_attempt.answer_revision_id = request.answer_revision_id
                return context

        class ConcurrentProvider:
            model_name = "fake-model"

            def generate(self, *, user_prompt, **kwargs):
                output = valid_output()
                if failed_revision in user_prompt:
                    output["criterion_assessments"][0]["evidence"][0]["quote"] = "invalid"
                return output

        client = self.client(ConcurrentProvider(), gateway=ConcurrentGateway())
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.post, "/api/agent", headers=HEADERS,
                json={**REQUEST, "answer_revision_id": revision})
                for revision in (failed_revision, successful_revision)]
            self.assertEqual([future.result().status_code for future in futures], [502, 200])
        failed, succeeded = sorted(self.observations.items, key=lambda item: item.attempt_count, reverse=True)
        self.assertEqual((failed.attempt_count, len(failed.attempt_failures)), (2, 2))
        self.assertEqual((succeeded.attempt_count, len(succeeded.attempt_failures)), (1, 0))
        self.assertNotEqual(failed.trace_id, succeeded.trace_id)

    def test_langfuse_metadata_serializes_history_and_sink_failure_is_local(self):
        class RecordingLangfuse:
            def start_observation(self, **kwargs):
                self.payload = kwargs
                return self

            def end(self):
                pass

        invalid = valid_output()
        invalid["criterion_assessments"][0]["evidence"][0]["quote"] = "invalid"
        self.client(FakeProvider([invalid, valid_output()])).post("/api/agent", headers=HEADERS, json=REQUEST)
        remote = RecordingLangfuse()
        LangfuseCoachingObservationSink(remote).record(self.observations.items[-1])
        metadata = remote.payload["metadata"]
        self.assertEqual(metadata["retry_count"], 1)
        self.assertEqual(metadata["attempt_failures"][0]["attempt"], 1)
        json.dumps(metadata)

        class FailingSink:
            def record(self, observation):
                raise RuntimeError("private-observation-key")

        with self.assertLogs(LOGGER) as logs:
            response = self.client(FakeProvider([valid_output()]), sink=FailingSink()).post(
                "/api/agent", headers=HEADERS, json=REQUEST,
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("COACHING_OBSERVATION_WRITE_FAILED", str(logs.output))
        self.assertNotIn("private-observation-key", str(logs.output))
        with self.assertRaises(ValidationError):
            CoachingAttemptFailure(attempt=1, stage="parse", error_code="private-secret")


if __name__ == "__main__":
    unittest.main()
