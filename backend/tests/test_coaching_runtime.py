from __future__ import annotations

import json
import os
import sys
import unittest
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import httpx
from openai import OpenAI

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.core.auth import AuthenticatedUser  # noqa: E402
from app.schemas.coaching import (  # noqa: E402
    CoachingAnalyzeRequest,
    CoachingContextBundle,
    JobContext,
    PracticeAttemptContext,
    QuestionContext,
)
from app.services.coaching_context import (  # noqa: E402
    DEMO_ANSWER_REVISION_ID,
    DEMO_JOB_SNAPSHOT_ID,
    DEMO_QUESTION_ID,
)
from app.services.coaching_skill import load_skill_bundle
from app.services.coaching_runtime import (  # noqa: E402
    CoachingProviderResult,
    McpLlmCoachingService,
    OpenAICompatibleJsonProvider,
    _normalize_json_envelope,
    build_coaching_service_from_env,
    load_fixed_skill_prompt,
    load_managed_coaching_prompt,
)
from app.services.coaching_errors import (  # noqa: E402
    CoachingBudgetExceededError,
    CoachingCreditsError,
    CoachingProviderError,
    CoachingTimeoutError,
)
from app.services.coaching_observability import (  # noqa: E402
    activate_coaching_trace,
    reset_coaching_trace,
)
from app.services.mcp_access import McpAccessTokenCodec  # noqa: E402
from app.services.mcp_context_gateway import McpStdioContextGateway  # noqa: E402
from services.llm import OutputContractError  # noqa: E402


REVISION_ID = UUID("70000000-0000-4000-8000-000000000001")
JOB_ID = UUID("80000000-0000-4000-8000-000000000001")
SESSION_ID = UUID("90000000-0000-4000-8000-000000000001")
USER = AuthenticatedUser("user-owner", "owner-token")


def context_bundle() -> CoachingContextBundle:
    now = datetime.now(UTC)
    return CoachingContextBundle(
        question=QuestionContext(
            question_id="preset-04",
            text="프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
            question_type="problem_solving",
            active_criterion_ids=["result_verification"],
            criteria_version="test-v1",
        ),
        practice_attempt=PracticeAttemptContext(
            answer_revision_id=REVISION_ID,
            user_id=USER.user_id,
            practice_session_id=SESSION_ID,
            question_id="preset-04",
            answer_segments=[
                {
                    "segment_id": "segment-1",
                    "text": "수정 후 같은 요청을 보내 200 응답을 확인했습니다.",
                }
            ],
            delivery_metrics={"cpm": 300},
            confirmed_at=now,
            expires_at=now + timedelta(hours=24),
        ),
        job_context=JobContext(
            job_snapshot_id=JOB_ID,
            user_id=USER.user_id,
            practice_session_id=SESSION_ID,
            source_url="https://example.invalid/job",
            captured_at=now,
            review_status="reviewed",
            requirements=[
                {"requirement_id": "J01-R1", "text": "회귀 확인", "category": "required"}
            ],
            expires_at=now + timedelta(hours=24),
        ),
    )


def valid_output():
    return {
        "job_alignment": [
            {
                "requirement_id": "J01-R1",
                "label": "related",
                "reason": "수정 결과 확인 경험이 관련됩니다.",
                "evidence": [
                    {"segment_id": "segment-1", "quote": "200 응답을 확인했습니다."}
                ],
            }
        ],
        "intent_assessment": {
            "label": "aligned",
            "reason": "조치 후 확인 방법과 결과가 있습니다.",
        },
        "criterion_assessments": [
            {
                "criterion_id": "result_verification",
                "assessment": "met",
                "reason": "동일 요청으로 결과를 확인했습니다.",
                "evidence": [
                    {
                        "segment_id": "segment-1",
                        "quote": "같은 요청을 보내 200 응답을 확인했습니다.",
                    }
                ],
                "needed": None,
            }
        ],
        "clarifying_question": None,
        "next_actions": [
            {
                "target_type": "criterion",
                "target_id": "result_verification",
                "action": "확인 조건을 유지해 다시 답해 보세요.",
            }
        ],
        "example_answer": (
            "수정 후 같은 요청을 보내 200 응답을 확인했습니다. "
            "이 확인 조건과 결과를 중심으로 설명하겠습니다."
        ),
    }


class FakeGateway:
    def __init__(self):
        self.calls = 0

    def load_context(self, user, request):
        self.calls += 1
        return context_bundle()


class FakeProvider:
    model_name = "fake-json-model"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0
        self.kwargs = []

    def generate(self, **kwargs):
        self.calls += 1
        self.kwargs.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


class RecordingDetailedSink:
    def __init__(self):
        self.generations = []
        self.validations = []

    def record_generation(self, observation):
        self.generations.append(observation)

    def record_validation(self, observation):
        self.validations.append(observation)


class RecordingGenerationLifecycleSink(RecordingDetailedSink):
    def __init__(self):
        super().__init__()
        self.started_generations = []

    def start_generation(self, observation):
        self.started_generations.append(observation)


class FakeResponse:
    def __init__(self, status_code=200, headers=None, usage=None, content=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.usage = usage or {}
        self.content = content

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": self.content
                        if self.content is not None
                        else __import__("json").dumps(
                            valid_output(), ensure_ascii=False
                        )
                    }
                }
            ],
            "usage": self.usage,
        }


class FakeHttp(httpx.Client):
    def __init__(self, responses=None):
        self.last_request = None
        self.requests = []
        self.responses = list(responses or [FakeResponse()])
        super().__init__(transport=httpx.MockTransport(self.handle))

    def handle(self, request):
        response = self.post(
            str(request.url), headers=dict(request.headers), json=json.loads(request.content)
        )
        return httpx.Response(
            response.status_code, headers=response.headers, json=response.json()
        )

    def post(self, url, **kwargs):
        self.last_request = {"url": url, **kwargs}
        self.requests.append(self.last_request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeManagedPrompt:
    def __init__(self, *, prompt: str, version: int, is_fallback: bool = False):
        self.prompt = prompt
        self.version = version
        self.is_fallback = is_fallback


class FakePromptClient:
    def __init__(self, prompt: FakeManagedPrompt):
        self.prompt = prompt
        self.calls = []

    def get_prompt(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.prompt


class FakePromptSink:
    def __init__(self, prompt: FakeManagedPrompt):
        self.client = FakePromptClient(prompt)
        self.managed_prompt = None

    def use_managed_prompt(self, prompt):
        self.managed_prompt = prompt


class CoachingRuntimeTest(unittest.TestCase):
    def test_gemini_cache_marks_only_system_and_tracks_hit(self):
        http = FakeHttp([FakeResponse(usage={
            "prompt_tokens": 12000, "completion_tokens": 40, "cost": 0.002,
            "prompt_tokens_details": {"cached_tokens": 10000, "cache_write_tokens": 0},
        })])
        sink = RecordingDetailedSink()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret", model_name="google/gemini-3.5-flash-lite",
            base_url="https://openrouter.ai/api/v1", http_client=http,
            observation_sink=sink,
        )
        provider.generate(system_prompt="fixed prompt and skill", user_prompt="private answer", schema={"type": "object"})
        messages = http.last_request["json"]["messages"]
        self.assertEqual(messages[0]["content"], [{
            "type": "text", "text": "fixed prompt and skill",
            "cache_control": {"type": "ephemeral"},
        }])
        self.assertEqual(messages[1], {"role": "user", "content": "private answer"})
        self.assertEqual(sink.generations[-1].cached_input_tokens, 10000)
        self.assertEqual(sink.generations[-1].cache_write_tokens, 0)


    def test_prompt_or_skill_update_changes_cached_content_identity(self):
        http = FakeHttp([FakeResponse(), FakeResponse()])
        sink = RecordingDetailedSink()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret", model_name="google/gemini-3.5-flash-lite",
            base_url="https://openrouter.ai/api/v1", http_client=http,
            observation_sink=sink,
        )
        for instructions in ("prompt v1 + skill v1", "prompt v2 + skill v2"):
            provider.generate(system_prompt=instructions, user_prompt="answer", schema={"type": "object"})
        self.assertNotEqual(sink.generations[0].cached_system_hash, sink.generations[1].cached_system_hash)
        self.assertIsNone(sink.generations[0].cached_input_tokens)


    def test_gemini_direct_provider_keeps_original_message_format(self):
        http = FakeHttp()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret", model_name="google/gemini-3.5-flash-lite",
            base_url="https://provider.example/v1", http_client=http,
        )
        provider.generate(system_prompt="fixed", user_prompt="answer", schema={"type": "object"})
        self.assertEqual(http.last_request["json"]["messages"][0]["content"], "fixed")



    def request(self):
        return CoachingAnalyzeRequest(
            action="analyze",
            question_id="preset-04",
            answer_revision_id=REVISION_ID,
            job_snapshot_id=JOB_ID,
        )

    def test_retries_invalid_quote_and_returns_only_validated_output(self):
        invalid = deepcopy(valid_output())
        invalid["criterion_assessments"][0]["evidence"][0]["quote"] = "없는 인용"
        provider = FakeProvider([invalid, valid_output()])
        service = McpLlmCoachingService(FakeGateway(), provider)

        result = service.analyze(USER, self.request())

        self.assertEqual(result.status.value, "ok")
        self.assertEqual(provider.calls, 2)
        repair_prompt = provider.kwargs[1]["user_prompt"]
        self.assertIn("[계약 보정 요청]", repair_prompt)
        self.assertIn("없는 인용", repair_prompt)
        self.assertIn("quote가 문장", repair_prompt)

    def test_records_each_contract_validation_on_the_active_trace(self):
        invalid = deepcopy(valid_output())
        invalid["criterion_assessments"][0]["evidence"][0]["quote"] = "없는 인용"
        provider = FakeProvider([invalid, valid_output()])
        sink = RecordingDetailedSink()
        service = McpLlmCoachingService(
            FakeGateway(), provider, observation_sink=sink
        )
        _, trace_token = activate_coaching_trace("trace-contract")
        try:
            result = service.analyze(USER, self.request())
        finally:
            reset_coaching_trace(trace_token)

        self.assertEqual(result.status.value, "ok")
        self.assertEqual(len(sink.validations), 2)
        self.assertEqual(
            [item.contract_attempt for item in sink.validations], [1, 2]
        )
        self.assertEqual([item.valid for item in sink.validations], [False, True])
        self.assertEqual(
            {item.trace_id for item in sink.validations}, {"trace-contract"}
        )

    def test_persistence_receives_actual_managed_prompt_and_skill_versions(self):
        class RecordingRepository:
            def __init__(self):
                self.kwargs = None

            def save(self, *args, **kwargs):
                self.kwargs = kwargs

        provider = FakeProvider([valid_output()])
        provider.prompt_version = "malhaebom-coaching@7"
        provider.skill_version = load_skill_bundle().catalog.skill_version
        repository = RecordingRepository()
        service = McpLlmCoachingService(
            FakeGateway(), provider, run_repository=repository,
        )
        with patch.dict(os.environ, {
            "COACHING_PROMPT_VERSION": "stale-local-prompt",
            "COACHING_SKILL_VERSION": "stale-local-skill",
        }):
            result = service.analyze(USER, self.request())
        self.assertEqual(result.status.value, "ok")
        self.assertEqual(repository.kwargs, {
            "prompt_version": "malhaebom-coaching@7",
            "skill_version": load_skill_bundle().catalog.skill_version,
        })

    def test_retries_provider_json_parse_contract_error(self):
        provider = FakeProvider(
            [OutputContractError(["LLM JSON 응답을 읽지 못했습니다."]), valid_output()]
        )
        sink = RecordingDetailedSink()
        service = McpLlmCoachingService(
            FakeGateway(), provider, observation_sink=sink
        )

        result = service.analyze(USER, self.request())

        self.assertEqual(result.status.value, "ok")
        self.assertEqual(provider.calls, 2)
        self.assertEqual([item.valid for item in sink.validations], [False, True])

    def test_unsupported_question_does_not_call_mcp_or_llm(self):
        gateway = FakeGateway()
        provider = FakeProvider([valid_output()])
        service = McpLlmCoachingService(gateway, provider)
        request = self.request().model_copy(update={"question_id": "preset-99"})

        result = service.analyze(USER, request)

        self.assertEqual(result.status.value, "unsupported")
        self.assertEqual(gateway.calls, 0)
        self.assertEqual(provider.calls, 0)

    def test_provider_requests_strict_json_schema(self):
        http = FakeHttp()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1/",
            http_client=http,
        )

        result = provider.generate(
            system_prompt="system",
            user_prompt="user",
            schema={"type": "object"},
        )

        self.assertEqual(result.output["intent_assessment"]["label"], "aligned")
        self.assertEqual(http.last_request["url"], "https://provider.example/v1/chat/completions")
        self.assertEqual(
            http.last_request["json"]["response_format"]["type"], "json_schema"
        )
        self.assertIsInstance(provider.client, OpenAI)
        self.assertEqual(provider.client.max_retries, 0)
        self.assertEqual(http.last_request["headers"]["authorization"], "Bearer secret")
        self.assertNotIn("temperature", http.last_request["json"])
        self.assertNotIn("secret", str(http.last_request["json"]))
        self.assertNotIn("provider", http.last_request["json"])

    def test_provider_starts_observation_before_sending_http_request(self):
        sink = RecordingGenerationLifecycleSink()

        class LifecycleHttp(FakeHttp):
            def post(self, url, **kwargs):
                if not sink.started_generations:
                    raise AssertionError("generation must start before provider HTTP")
                return super().post(url, **kwargs)

        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1",
            http_client=LifecycleHttp(),
            observation_sink=sink,
        )

        provider.generate(
            system_prompt="system", user_prompt="user", schema={"type": "object"}
        )

        self.assertEqual(len(sink.started_generations), 1)
        self.assertEqual(len(sink.generations), 1)
        self.assertEqual(
            sink.started_generations[0].generation_id,
            sink.generations[0].generation_id,
        )

    def test_provider_finishes_generation_for_unexpected_sdk_error(self):
        sink = RecordingGenerationLifecycleSink()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1",
            observation_sink=sink,
        )

        def raise_unexpected(**kwargs):
            del kwargs
            raise RuntimeError("unexpected SDK failure")

        provider.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    with_raw_response=SimpleNamespace(create=raise_unexpected)
                )
            )
        )

        with self.assertRaisesRegex(RuntimeError, "unexpected SDK failure"):
            provider.generate(
                system_prompt="system",
                user_prompt="user",
                schema={"type": "object"},
            )

        self.assertEqual(len(sink.started_generations), 1)
        self.assertEqual(len(sink.generations), 1)
        self.assertEqual(sink.generations[0].outcome, "unexpected_error")
        self.assertEqual(
            sink.started_generations[0].generation_id,
            sink.generations[0].generation_id,
        )

    def test_sdk_does_not_add_retries_outside_transport_policy(self):
        http = FakeHttp([FakeResponse(503)])
        provider = OpenAICompatibleJsonProvider(
            api_key="secret", model_name="provider/model",
            base_url="https://provider.example/v1", http_client=http,
            max_transport_attempts=1,
        )
        with self.assertRaises(CoachingProviderError):
            provider.generate(system_prompt="system", user_prompt="user", schema={"type": "object"})
        self.assertEqual(len(http.requests), 1)

    def test_openai_gpt5_uses_fully_required_strict_schema(self):
        http = FakeHttp()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="openai/gpt-5.6-luna",
            base_url="https://openrouter.ai/api/v1",
            http_client=http,
        )
        schema = {
            "type": "object",
            "properties": {
                "outer": {
                    "type": "object",
                    "properties": {"optional": {"type": ["string", "null"]}},
                }
            },
        }

        provider.generate(system_prompt="system", user_prompt="user", schema=schema)

        sent = http.last_request["json"]["response_format"]["json_schema"]["schema"]
        self.assertEqual(sent["required"], ["outer"])
        self.assertFalse(sent["additionalProperties"])
        self.assertEqual(sent["properties"]["outer"]["required"], ["optional"])
        self.assertNotIn("required", schema)

    def test_openrouter_requires_structured_output_capable_provider(self):
        http = FakeHttp()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="openai/gpt-4o-mini",
            base_url="https://openrouter.ai/api/v1",
            http_client=http,
        )

        provider.generate(
            system_prompt="system",
            user_prompt="user",
            schema={"type": "object"},
        )

        self.assertEqual(
            http.last_request["json"]["provider"], {"require_parameters": True}
        )

    def test_provider_retries_5xx_once_with_bounded_backoff(self):
        http = FakeHttp(
            [
                FakeResponse(500),
                FakeResponse(
                    200,
                    usage={"prompt_tokens": 100, "completion_tokens": 40, "cost": 0.01},
                ),
            ]
        )
        sleeps = []
        sink = RecordingDetailedSink()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1",
            http_client=http,
            sleeper=sleeps.append,
            observation_sink=sink,
        )

        trace_context, trace_token = activate_coaching_trace("trace-transport")
        try:
            result = provider.generate(
                system_prompt="system",
                user_prompt="user",
                schema={"type": "object"},
            )
        finally:
            reset_coaching_trace(trace_token)

        self.assertEqual(result.output["intent_assessment"]["label"], "aligned")
        self.assertEqual(len(http.requests), 2)
        self.assertEqual(sleeps, [0.5])
        self.assertEqual(
            [item.outcome for item in sink.generations],
            ["provider_error", "success"],
        )
        self.assertEqual(
            {item.trace_id for item in sink.generations}, {"trace-transport"}
        )
        self.assertTrue(sink.generations[0].will_retry)
        self.assertEqual(trace_context.input_tokens, 100)
        self.assertEqual(trace_context.output_tokens, 40)
        self.assertEqual(trace_context.cost_usd, 0.01)

    def test_provider_caps_retry_after_before_retrying(self):
        http = FakeHttp(
            [FakeResponse(429, {"Retry-After": "99"}), FakeResponse(200)]
        )
        sleeps = []
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1",
            http_client=http,
            sleeper=sleeps.append,
        )

        provider.generate(
            system_prompt="system",
            user_prompt="user",
            schema={"type": "object"},
        )

        self.assertEqual(sleeps, [2.0])

    def test_provider_stops_after_timeout_attempt_limit(self):
        timeout = httpx.ReadTimeout("timed out")
        http = FakeHttp([timeout, timeout])
        sleeps = []
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1",
            http_client=http,
            sleeper=sleeps.append,
        )

        with self.assertRaises(CoachingTimeoutError):
            provider.generate(
                system_prompt="system",
                user_prompt="user",
                schema={"type": "object"},
            )

        self.assertEqual(len(http.requests), 2)
        self.assertEqual(sleeps, [0.5])

    def test_provider_does_not_retry_non_retryable_4xx(self):
        http = FakeHttp([FakeResponse(400), FakeResponse(200)])
        sleeps = []
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1",
            http_client=http,
            sleeper=sleeps.append,
        )

        with self.assertRaises(CoachingProviderError):
            provider.generate(
                system_prompt="system",
                user_prompt="user",
                schema={"type": "object"},
            )

        self.assertEqual(len(http.requests), 1)
        self.assertEqual(sleeps, [])

    def test_service_blocks_response_when_reported_cost_exceeds_limit(self):
        invalid = deepcopy(valid_output())
        invalid["criterion_assessments"][0]["evidence"][0]["quote"] = "없는 인용"
        provider = FakeProvider(
            [
                CoachingProviderResult(output=invalid, cost_usd=0.06),
                CoachingProviderResult(output=valid_output(), cost_usd=0.06),
            ]
        )
        service = McpLlmCoachingService(
            FakeGateway(), provider, max_cost_usd=0.10
        )

        with self.assertRaises(CoachingBudgetExceededError):
            service.analyze(USER, self.request())

        self.assertEqual(provider.calls, 2)

    def test_service_counts_billed_invalid_json_toward_cost_limit(self):
        http = FakeHttp(
            [
                FakeResponse(200, usage={"cost": 0.06}, content="not-json"),
                FakeResponse(200, usage={"cost": 0.06}),
            ]
        )
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1",
            http_client=http,
            sleeper=lambda _: None,
        )
        service = McpLlmCoachingService(
            FakeGateway(), provider, max_cost_usd=0.10
        )

        with self.assertRaises(CoachingBudgetExceededError):
            service.analyze(USER, self.request())

        self.assertEqual(len(http.requests), 2)

    def test_normalize_json_envelope_strips_markdown_code_fences_safely(self):
        # 1. Pure json string remains unchanged
        pure_json = '{"status": "ok"}'
        self.assertEqual(_normalize_json_envelope(pure_json), pure_json)

        # 2. ```json ... ``` code fence stripped
        fenced_json = '```json\n{"status": "ok"}\n```'
        self.assertEqual(_normalize_json_envelope(fenced_json), '{"status": "ok"}')

        # 3. ``` ... ``` code fence stripped
        fenced_plain = '```\n{"status": "ok"}\n```'
        self.assertEqual(_normalize_json_envelope(fenced_plain), '{"status": "ok"}')

        # 4. Text before or after code fence is not silently extracted (conservative)
        surrounded = 'Here is the result:\n```json\n{"status": "ok"}\n```'
        self.assertEqual(_normalize_json_envelope(surrounded), surrounded)

        trailing = '```json\n{"status": "ok"}\n```\nHope this helps!'
        self.assertEqual(_normalize_json_envelope(trailing), trailing)

        # 5. Non-string inputs raise TypeError
        with self.assertRaises(TypeError):
            _normalize_json_envelope(123)

    def test_provider_accepts_markdown_code_fenced_json_response(self):
        fenced = "```json\n" + __import__("json").dumps(valid_output(), ensure_ascii=False) + "\n```"
        http = FakeHttp([FakeResponse(200, content=fenced)])
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="provider/model",
            base_url="https://provider.example/v1",
            http_client=http,
        )

        result = provider.generate(
            system_prompt="system",
            user_prompt="user",
            schema={"type": "object"},
        )

        self.assertEqual(result.output["intent_assessment"]["label"], "aligned")

    def test_provider_limits_completion_tokens_and_identifies_insufficient_credits(self):
        http = FakeHttp()
        provider = OpenAICompatibleJsonProvider(
            api_key="secret",
            model_name="google/gemini-3.8-flash",
            base_url="https://openrouter.ai/api/v1",
            http_client=http,
            max_tokens=3072,
        )
        provider.generate(system_prompt="system", user_prompt="user", schema={"type": "object"})
        self.assertEqual(http.last_request["json"]["max_tokens"], 3072)

        http.responses = [FakeResponse(402)]
        with self.assertRaises(CoachingCreditsError):
            provider.generate(system_prompt="system", user_prompt="user", schema={"type": "object"})

    def test_real_stdio_mcp_gateway_reads_three_demo_tools(self):
        secret = "test-only-secret-with-at-least-32-characters"
        request = CoachingAnalyzeRequest(
            action="analyze",
            question_id=DEMO_QUESTION_ID,
            answer_revision_id=DEMO_ANSWER_REVISION_ID,
            job_snapshot_id=DEMO_JOB_SNAPSHOT_ID,
        )
        with patch.dict(
            os.environ,
            {"COACHING_MOCK_ENABLED": "true", "MCP_INTERNAL_SECRET": secret},
        ):
            result = McpStdioContextGateway(
                McpAccessTokenCodec(secret), timeout_seconds=20
            ).load_context(USER, request)

        self.assertEqual(result.question.question_id, DEMO_QUESTION_ID)
        self.assertEqual(result.practice_attempt.user_id, USER.user_id)
        self.assertEqual(result.job_context.requirements[0].requirement_id, "J01-R1")

    def test_ollama_settings_use_chat_model_and_openai_compatible_url(self):
        with patch.dict(
            os.environ,
            {
                "COACHING_PROVIDER": "ollama",
                "COACHING_MODEL": "qwen2.5-coder:latest",
                "COACHING_OLLAMA_URL": "http://host.docker.internal:11434",
                "COACHING_LLM_TIMEOUT_SECONDS": "",
                "MCP_INTERNAL_SECRET": "test-only-secret-with-at-least-32-characters",
                "SUPABASE_URL": "https://project.supabase.co",
                "SUPABASE_PUBLISHABLE_KEY": "publishable",
                "SUPABASE_SERVICE_ROLE_KEY": "service-secret",
            },
            clear=True,
        ):
            service = build_coaching_service_from_env()

        self.assertIsNotNone(service)
        assert service is not None
        self.assertEqual(service.model_name, "qwen2.5-coder:latest")
        self.assertEqual(
            service.provider.base_url, "http://host.docker.internal:11434/v1"
        )
        self.assertEqual(service.provider.api_key, "ollama")
        self.assertEqual(service.provider.http.timeout.read, 180.0)

    def test_invalid_timeout_configuration_disables_live_coaching_safely(self):
        with patch.dict(
            os.environ,
            {
                "COACHING_LLM_API_KEY": "provider-key",
                "COACHING_LLM_MODEL": "provider/model",
                "COACHING_LLM_TIMEOUT_SECONDS": "not-a-number",
                "MCP_INTERNAL_SECRET": "test-only-secret-with-at-least-32-characters",
                "SUPABASE_URL": "https://project.supabase.co",
                "SUPABASE_PUBLISHABLE_KEY": "publishable",
                "SUPABASE_SERVICE_ROLE_KEY": "service-secret",
            },
            clear=True,
        ):
            self.assertIsNone(build_coaching_service_from_env())

    def test_managed_prompt_uses_requested_label_and_links_sink(self):
        managed = FakeManagedPrompt(
            prompt="managed prompt\nprompt_version={{prompt_version}}; skill_version={{skill_version}}\n{{skill_text}}",
            version=7,
        )
        sink = FakePromptSink(managed)
        with patch.dict(
            os.environ,
            {
                "LANGFUSE_PROMPT_NAME": "malhaebom-coaching",
                "LANGFUSE_PROMPT_LABEL": "candidate",
                "LANGFUSE_PROMPT_CACHE_TTL_SECONDS": "0",
            },
            clear=True,
        ):
            prompt, version = load_managed_coaching_prompt(sink)

        self.assertTrue(prompt.startswith("managed prompt\n"))
        self.assertIn(load_skill_bundle().rules_text, prompt)
        self.assertIn("prompt_version=malhaebom-coaching@7", prompt)
        self.assertEqual(version, "malhaebom-coaching@7")
        self.assertIs(sink.managed_prompt, managed)
        self.assertEqual(sink.client.calls[0][1]["label"], "candidate")
        self.assertEqual(sink.client.calls[0][1]["cache_ttl_seconds"], 0)

    def test_managed_prompt_fallback_keeps_local_version(self):
        fallback = FakeManagedPrompt(
            prompt="ignored fallback", version=0, is_fallback=True
        )
        sink = FakePromptSink(fallback)
        with patch.dict(
            os.environ,
            {
                "LANGFUSE_PROMPT_NAME": "malhaebom-coaching",
                "COACHING_PROMPT_VERSION": "coaching-output-local",
            },
            clear=True,
        ):
            prompt, version = load_managed_coaching_prompt(sink)

        self.assertIn("prompt_version=coaching-output-local", prompt)
        self.assertIn("skill_version=interview-coach-v6", prompt)
        self.assertEqual(version, "coaching-output-local")
        self.assertIsNone(sink.managed_prompt)


if __name__ == "__main__":
    unittest.main()
