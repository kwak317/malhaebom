from __future__ import annotations
from app.services.loading_progress import report_progress

import json
import hashlib
import os
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from uuid import uuid4

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.core.auth import AuthenticatedUser
from app.core.supabase_settings import SupabaseSettings, SupabaseSettingsError
from app.schemas.coaching import (
    CoachingAnalyzeRequest,
    CoachingContextBundle,
    CoachingLLMOutput,
    CoachingResponse,
    TerminalResponseReason,
)
from app.services.coaching_errors import (
    CoachingBudgetExceededError,
    CoachingCreditsError,
    CoachingProviderError,
    CoachingRateLimitError,
    CoachingTimeoutError,
)
from app.services.coaching_diagnostics import (
    coaching_step, finish_coaching_success, record_coaching_failure, start_coaching_attempt,
)
from app.services.mcp_access import McpAccessTokenCodec
from app.services.mcp_context_gateway import McpStdioContextGateway
from app.services.prompt_templates import PromptTemplateError, compose_skill_prompt
from app.services.coaching_prompt import (
    build_coaching_system_prompt,
    build_contract_repair_user_prompt,
)
from app.services.coaching_skill import load_skill_bundle
from app.services.coaching_questions import PRESET_QUESTION_IDS, is_custom_coaching_question_id
from app.services.coaching_observability import (
    DEFAULT_PROMPT_VERSION,
    DEFAULT_SKILL_VERSION,
    CoachingGenerationObservation,
    CoachingObservationSink,
    CoachingValidationObservation,
    observation_trace_id,
    record_generation_safely,
    record_validation_safely,
    start_generation_safely,
)
from app.services.supabase_coaching_runs import SupabaseCoachingRunRepository
from services.llm import (
    OutputContractError,
    build_terminal_response,
    validate_and_build_response,
)

@dataclass(frozen=True)
class CoachingProviderResult:
    output: dict[str, object]
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class ProviderOutputContractError(OutputContractError):
    """provider가 비용 정보를 포함해 반환한 읽을 수 없는 출력."""

    def __init__(
        self,
        violations: list[str],
        *,
        cost_usd: float | None = None,
        previous_output: object = None,
    ) -> None:
        self.cost_usd = cost_usd
        self.previous_output = previous_output
        super().__init__(violations)


class ContextGateway(Protocol):
    def load_context(
        self, user: AuthenticatedUser, request: CoachingAnalyzeRequest
    ) -> CoachingContextBundle: ...


class CoachingJsonProvider(Protocol):
    model_name: str

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, object],
        contract_attempt: int = 1,
    ) -> CoachingProviderResult | dict[str, object]: ...


class OpenAICompatibleJsonProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str,
        timeout_seconds: float = 25.0,
        max_transport_attempts: int = 2,
        backoff_seconds: float = 0.5,
        max_backoff_seconds: float = 2.0,
        http_client: httpx.Client | Any | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        observation_sink: CoachingObservationSink | Any | None = None,
        prompt_version: str | None = None,
        skill_version: str | None = None,
        schema_name: str = "malhaebom_coaching",
        require_provider_parameters: bool = True,
        max_tokens: int | None = None,
    ) -> None:
        if not api_key.strip() or not model_name.strip() or not schema_name.strip():
            raise ValueError("코칭 LLM API 키와 모델 이름이 필요합니다.")
        if not 1 <= max_transport_attempts <= 3:
            raise ValueError("LLM 전송 시도 횟수는 1~3이어야 합니다.")
        if backoff_seconds < 0 or max_backoff_seconds < backoff_seconds:
            raise ValueError("LLM backoff 설정이 올바르지 않습니다.")
        if max_tokens is not None and max_tokens <= 0:
            raise ValueError("모델 출력 토큰 한도는 양수여야 합니다.")
        self.schema_name = schema_name.strip()
        self.require_provider_parameters = require_provider_parameters
        self.max_tokens = max_tokens
        self.api_key = api_key.strip()
        self.model_name = model_name.strip()
        self.base_url = base_url.strip().rstrip("/")
        self.max_transport_attempts = max_transport_attempts
        self.backoff_seconds = backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.http = http_client or httpx.Client(timeout=timeout_seconds)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout_seconds,
            max_retries=0,
            http_client=self.http,
        )
        self.sleeper = sleeper
        self.observation_sink = observation_sink
        self.prompt_version = prompt_version or os.getenv(
            "COACHING_PROMPT_VERSION", DEFAULT_PROMPT_VERSION
        )
        self.skill_version = skill_version or os.getenv(
            "COACHING_SKILL_VERSION", DEFAULT_SKILL_VERSION
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, object],
        contract_attempt: int = 1,
    ) -> CoachingProviderResult:
        # Cache only immutable instructions. OpenRouter manages cache identity by
        # content, so any Prompt/Skill content update creates a different cache.
        cache_enabled = (
            "openrouter.ai" in self.base_url
            and self.model_name.startswith("google/gemini-3.5-")
        )
        system_content: object = system_prompt
        if cache_enabled:
            system_content = [{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }]
        payload: dict[str, object] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": self.schema_name,
                    "strict": True,
                    "schema": (
                        _strict_json_schema(schema)
                        if self.model_name.startswith("openai/gpt-5")
                        else schema
                    ),
                },
            },
        }
        if "openrouter.ai" in self.base_url and self.require_provider_parameters:
            payload["provider"] = {"require_parameters": True}
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        request_options = dict(payload)
        if "provider" in request_options:
            request_options["extra_body"] = {"provider": request_options.pop("provider")}
        response = None
        last_error: APIConnectionError | None = None
        trace_id = observation_trace_id()
        for transport_attempt in range(self.max_transport_attempts):
            started = time.perf_counter()
            attempt_number = transport_attempt + 1
            generation_id = uuid4().hex
            self._start_generation(
                trace_id=trace_id,
                generation_id=generation_id,
                contract_attempt=contract_attempt,
                transport_attempt=attempt_number,
            )
            try:
                sdk_response = self.client.chat.completions.with_raw_response.create(
                    **request_options
                )
                response = sdk_response.http_response
                last_error = None
            except APITimeoutError as error:
                last_error = error
                will_retry = attempt_number < self.max_transport_attempts
                self._record_generation(
                    trace_id=trace_id,
                    generation_id=generation_id,
                    contract_attempt=contract_attempt,
                    transport_attempt=attempt_number,
                    outcome="timeout",
                    retry_reason="timeout" if will_retry else None,
                    will_retry=will_retry,
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
                if not will_retry:
                    record_coaching_failure("provider", "COACHING_TIMEOUT")
                    raise CoachingTimeoutError() from error
                self.sleeper(self._backoff_delay(transport_attempt))
                continue
            except APIConnectionError as error:
                last_error = error
                will_retry = attempt_number < self.max_transport_attempts
                self._record_generation(
                    trace_id=trace_id,
                    generation_id=generation_id,
                    contract_attempt=contract_attempt,
                    transport_attempt=attempt_number,
                    outcome="network_error",
                    retry_reason="network_error" if will_retry else None,
                    will_retry=will_retry,
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
                if not will_retry:
                    record_coaching_failure("provider", "COACHING_PROVIDER_CONNECTION_FAILED")
                    raise CoachingProviderError() from error
                self.sleeper(self._backoff_delay(transport_attempt))
                continue
            except APIStatusError as error:
                response = error.response
                last_error = None
            except Exception:
                self._record_generation(
                    trace_id=trace_id,
                    generation_id=generation_id,
                    contract_attempt=contract_attempt,
                    transport_attempt=attempt_number,
                    outcome="unexpected_error",
                    will_retry=False,
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
                raise

            if response.status_code in (200, 201):
                break
            if response.status_code == 429:
                retry_after = self._retry_after(response.headers.get("Retry-After"))
                will_retry = attempt_number < self.max_transport_attempts
                self._record_generation(
                    trace_id=trace_id,
                    generation_id=generation_id,
                    contract_attempt=contract_attempt,
                    transport_attempt=attempt_number,
                    status_code=response.status_code,
                    outcome="rate_limited",
                    retry_reason="rate_limited" if will_retry else None,
                    will_retry=will_retry,
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
                if not will_retry:
                    record_coaching_failure("provider", "COACHING_RATE_LIMITED")
                    raise CoachingRateLimitError(
                        int(retry_after) if retry_after is not None else None
                    )
                self.sleeper(
                    retry_after
                    if retry_after is not None
                    else self._backoff_delay(transport_attempt)
                )
                continue
            if response.status_code >= 500:
                will_retry = attempt_number < self.max_transport_attempts
                self._record_generation(
                    trace_id=trace_id,
                    generation_id=generation_id,
                    contract_attempt=contract_attempt,
                    transport_attempt=attempt_number,
                    status_code=response.status_code,
                    outcome="provider_error",
                    retry_reason="server_error" if will_retry else None,
                    will_retry=will_retry,
                    latency_ms=(time.perf_counter() - started) * 1000,
                )
                if not will_retry:
                    record_coaching_failure("provider", "COACHING_PROVIDER_HTTP_ERROR")
                    raise CoachingProviderError()
                self.sleeper(self._backoff_delay(transport_attempt))
                continue
            self._record_generation(
                trace_id=trace_id,
                generation_id=generation_id,
                contract_attempt=contract_attempt,
                transport_attempt=attempt_number,
                status_code=response.status_code,
                outcome="provider_error",
                will_retry=False,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
            if response.status_code == 402:
                record_coaching_failure("provider", "COACHING_CREDITS_EXHAUSTED")
                raise CoachingCreditsError()
            record_coaching_failure("provider", "COACHING_PROVIDER_HTTP_ERROR")
            raise CoachingProviderError()

        if response is None:
            raise CoachingProviderError() from last_error
        response_payload: object = None
        content: object = None
        input_tokens = output_tokens = None
        cost_usd = None
        try:
            response_payload = response.json()
            if not isinstance(response_payload, dict):
                raise TypeError("provider response must be an object")
            input_tokens, output_tokens, cost_usd = _usage_from_payload(
                response_payload
            )
            content = response_payload["choices"][0]["message"]["content"]
            normalized_content = _normalize_json_envelope(content)
            value = json.loads(normalized_content)
        except (ValueError, KeyError, IndexError, TypeError) as error:
            self._record_generation(
                trace_id=trace_id,
                generation_id=generation_id,
                contract_attempt=contract_attempt,
                transport_attempt=attempt_number,
                status_code=response.status_code,
                outcome="contract_error",
                will_retry=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                cache_usage=response_payload,
                cached_system_hash=hashlib.sha256(system_prompt.encode()).hexdigest() if cache_enabled else None,
            )
            record_coaching_failure("parse", "COACHING_JSON_PARSE_FAILED")
            raise ProviderOutputContractError(
                ["LLM JSON 응답을 읽지 못했습니다."],
                cost_usd=cost_usd,
                previous_output=content,
            ) from error
        if not isinstance(value, dict):
            self._record_generation(
                trace_id=trace_id,
                generation_id=generation_id,
                contract_attempt=contract_attempt,
                transport_attempt=attempt_number,
                status_code=response.status_code,
                outcome="contract_error",
                will_retry=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                cache_usage=response_payload,
                cached_system_hash=hashlib.sha256(system_prompt.encode()).hexdigest() if cache_enabled else None,
            )
            record_coaching_failure("parse", "COACHING_JSON_OBJECT_REQUIRED")
            raise ProviderOutputContractError(
                ["LLM 응답은 JSON 객체여야 합니다."],
                cost_usd=cost_usd,
                previous_output=value,
            )
        self._record_generation(
            trace_id=trace_id,
            generation_id=generation_id,
            contract_attempt=contract_attempt,
            transport_attempt=attempt_number,
            status_code=response.status_code,
            outcome="success",
            will_retry=False,
            latency_ms=(time.perf_counter() - started) * 1000,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            output_is_json_object=True,
            cache_usage=response_payload,
            cached_system_hash=hashlib.sha256(system_prompt.encode()).hexdigest() if cache_enabled else None,
        )
        return CoachingProviderResult(
            output=value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

    def _record_generation(
        self,
        *,
        trace_id: str,
        generation_id: str,
        contract_attempt: int,
        transport_attempt: int,
        outcome: str,
        will_retry: bool,
        latency_ms: float,
        status_code: int | None = None,
        retry_reason: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        output_is_json_object: bool = False,
        cache_usage: object = None,
        cached_system_hash: str | None = None,
    ) -> None:
        record_generation_safely(
            self.observation_sink,
            CoachingGenerationObservation(
                trace_id=trace_id,
                generation_id=generation_id,
                model=self.model_name,
                prompt_version=self.prompt_version,
                skill_version=self.skill_version,
                contract_attempt=contract_attempt,
                transport_attempt=transport_attempt,
                repair_prompt=contract_attempt > 1,
                status_code=status_code,
                outcome=outcome,
                retry_reason=retry_reason,
                will_retry=will_retry,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                output_is_json_object=output_is_json_object,
                cached_input_tokens=_cache_usage_value(cache_usage, "cached_tokens"),
                cache_write_tokens=_cache_usage_value(cache_usage, "cache_write_tokens"),
                cached_system_hash=cached_system_hash,
            ),
        )

    def _start_generation(
        self,
        *,
        trace_id: str,
        generation_id: str,
        contract_attempt: int,
        transport_attempt: int,
    ) -> None:
        start_generation_safely(
            self.observation_sink,
            CoachingGenerationObservation(
                trace_id=trace_id,
                generation_id=generation_id,
                model=self.model_name,
                prompt_version=self.prompt_version,
                skill_version=self.skill_version,
                contract_attempt=contract_attempt,
                transport_attempt=transport_attempt,
                repair_prompt=contract_attempt > 1,
                outcome="pending",
                will_retry=False,
                latency_ms=0.0,
            ),
        )

    def _backoff_delay(self, transport_attempt: int) -> float:
        return min(
            self.backoff_seconds * (2**transport_attempt),
            self.max_backoff_seconds,
        )

    def _retry_after(self, value: str | None) -> float | None:
        if value is None:
            return None
        try:
            seconds = float(value)
        except ValueError:
            return None
        if seconds < 0:
            return None
        return min(seconds, self.max_backoff_seconds)


class McpLlmCoachingService:
    def __init__(
        self,
        context_gateway: ContextGateway,
        provider: CoachingJsonProvider,
        *,
        run_repository: Any | None = None,
        max_attempts: int = 2,
        max_cost_usd: float = 0.10,
        observation_sink: CoachingObservationSink | Any | None = None,
        system_prompt: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("LLM 계약 시도 횟수는 1 이상이어야 합니다.")
        if max_cost_usd <= 0:
            raise ValueError("LLM 요청 비용 상한은 0보다 커야 합니다.")
        self.context_gateway = context_gateway
        self.provider = provider
        self.run_repository = run_repository
        self.max_attempts = max_attempts
        self.max_cost_usd = max_cost_usd
        self.observation_sink = observation_sink
        self.model_name = provider.model_name
        self.system_prompt = system_prompt or load_fixed_skill_prompt()
        self.prompt_version = prompt_version or getattr(
            provider,
            "prompt_version",
            os.getenv("COACHING_PROMPT_VERSION", DEFAULT_PROMPT_VERSION),
        )
        self.skill_version = getattr(
            provider,
            "skill_version",
            os.getenv("COACHING_SKILL_VERSION", DEFAULT_SKILL_VERSION),
        )

    def analyze(
        self, user: AuthenticatedUser, request: CoachingAnalyzeRequest
    ) -> CoachingResponse:
        if request.question_id not in PRESET_QUESTION_IDS and not is_custom_coaching_question_id(request.question_id):
            return build_terminal_response(
                TerminalResponseReason(
                    status="unsupported",
                    reason="기본 질문 또는 저장된 직접 입력 질문을 선택해 주세요.",
                )
            )
        report_progress("확정 답변과 질문·공고 기준을 확인하고 있어요…")
        with coaching_step("context", "COACHING_CONTEXT_LOAD_FAILED"):
            context = self.context_gateway.load_context(user, request)
        user_prompt = _context_prompt(context)
        last_error: OutputContractError | None = None
        previous_output: object = None
        total_cost_usd = 0.0
        for attempt in range(self.max_attempts):
            start_coaching_attempt()
            attempt_user_prompt = user_prompt
            if last_error is not None:
                attempt_user_prompt = build_contract_repair_user_prompt(
                    user_prompt,
                    previous_output,
                    last_error.violations,
                )
            try:
                report_progress("답변의 강점과 보완할 내용을 분석하고 있어요…" if not attempt else "코칭 결과를 다시 분석하고 있어요…")
                with coaching_step("provider", "COACHING_PROVIDER_CALL_FAILED"):
                    provider_result = self.provider.generate(
                        system_prompt=self.system_prompt,
                        user_prompt=attempt_user_prompt,
                        schema=CoachingLLMOutput.model_json_schema(),
                        contract_attempt=attempt + 1,
                    )
            except OutputContractError as error:
                if isinstance(error, ProviderOutputContractError):
                    if error.cost_usd is not None:
                        total_cost_usd += error.cost_usd
                        if total_cost_usd > self.max_cost_usd:
                            raise CoachingBudgetExceededError(
                                "coaching request cost limit exceeded"
                            ) from error
                self._record_validation(
                    contract_attempt=attempt + 1,
                    valid=False,
                    error_count=len(error.violations),
                    latency_ms=0.0,
                )
                if isinstance(error, ProviderOutputContractError):
                    previous_output = error.previous_output
                last_error = error
                if attempt + 1 >= self.max_attempts:
                    raise
                continue
            if isinstance(provider_result, CoachingProviderResult):
                raw_output = provider_result.output
                if provider_result.cost_usd is not None:
                    total_cost_usd += provider_result.cost_usd
                    if total_cost_usd > self.max_cost_usd:
                        raise CoachingBudgetExceededError(
                            "coaching request cost limit exceeded"
                        )
            else:
                raw_output = provider_result
            validation_started = time.perf_counter()
            try:
                report_progress("코칭 결과와 답변 인용 근거를 검증하고 있어요…")
                with coaching_step("validation", "COACHING_OUTPUT_VALIDATION_FAILED"):
                    result = validate_and_build_response(
                        raw_output, context.to_validation_context()
                    )
                self._record_validation(
                    contract_attempt=attempt + 1,
                    valid=True,
                    error_count=0,
                    latency_ms=(time.perf_counter() - validation_started) * 1000,
                )
                if self.run_repository is not None:
                    report_progress("검증된 분석 결과를 저장하고 있어요…")
                    with coaching_step("persistence", "COACHING_RESULT_SAVE_FAILED"):
                        self.run_repository.save(
                            user, request, result, context, self.model_name,
                            prompt_version=self.prompt_version,
                            skill_version=self.skill_version,
                        )
                finish_coaching_success()
                return result
            except OutputContractError as error:
                self._record_validation(
                    contract_attempt=attempt + 1,
                    valid=False,
                    error_count=len(error.violations),
                    latency_ms=(time.perf_counter() - validation_started) * 1000,
                )
                previous_output = raw_output
                last_error = error
                if attempt + 1 >= self.max_attempts:
                    raise
        raise last_error or OutputContractError(["코칭 출력을 만들지 못했습니다."])

    def _record_validation(
        self,
        *,
        contract_attempt: int,
        valid: bool,
        error_count: int,
        latency_ms: float,
    ) -> None:
        record_validation_safely(
            self.observation_sink,
            CoachingValidationObservation(
                trace_id=observation_trace_id(),
                prompt_version=self.prompt_version,
                skill_version=self.skill_version,
                contract_attempt=contract_attempt,
                valid=valid,
                error_count=error_count,
                latency_ms=latency_ms,
            ),
        )


def load_fixed_skill_prompt() -> str:
    bundle = load_skill_bundle()
    prompt_version = os.getenv(
        "COACHING_PROMPT_VERSION", DEFAULT_PROMPT_VERSION
    ).strip() or DEFAULT_PROMPT_VERSION
    skill_version = os.getenv(
        "COACHING_SKILL_VERSION", bundle.catalog.skill_version
    ).strip() or bundle.catalog.skill_version
    return build_coaching_system_prompt(
        bundle.rules_text,
        prompt_version,
        skill_version,
    )


def load_managed_coaching_prompt(
    observation_sink: CoachingObservationSink | Any | None,
) -> tuple[str, str]:
    """production label을 읽고 실패하면 버전 고정 로컬 Prompt를 사용한다."""

    local_prompt = load_fixed_skill_prompt()
    local_version = os.getenv(
        "COACHING_PROMPT_VERSION", DEFAULT_PROMPT_VERSION
    ).strip() or DEFAULT_PROMPT_VERSION
    prompt_name = os.getenv("LANGFUSE_PROMPT_NAME", "").strip()
    client = getattr(observation_sink, "client", None)
    if not prompt_name or client is None:
        return local_prompt, local_version

    prompt_label = os.getenv("LANGFUSE_PROMPT_LABEL", "production").strip()
    try:
        cache_ttl_seconds = max(
            0,
            int(os.getenv("LANGFUSE_PROMPT_CACHE_TTL_SECONDS", "60").strip()),
        )
        managed_prompt = client.get_prompt(
            prompt_name,
            label=prompt_label or "production",
            type="text",
            cache_ttl_seconds=cache_ttl_seconds,
            fallback=local_prompt,
        )
    except (TypeError, ValueError, OSError):
        return local_prompt, local_version
    except Exception:
        return local_prompt, local_version

    if getattr(managed_prompt, "is_fallback", False):
        return local_prompt, local_version
    prompt_text = getattr(managed_prompt, "prompt", None)
    prompt_number = getattr(managed_prompt, "version", None)
    if not isinstance(prompt_text, str) or not prompt_text.strip():
        return local_prompt, local_version
    bundle = load_skill_bundle()
    skill_version = os.getenv("COACHING_SKILL_VERSION", bundle.catalog.skill_version).strip() or bundle.catalog.skill_version
    managed_version = f"{prompt_name}@{prompt_number}"
    try:
        rendered_prompt = compose_skill_prompt(
            prompt_text, skill_text=bundle.rules_text, skill_version=skill_version,
            prompt_version=managed_version,
        )
    except PromptTemplateError:
        return local_prompt, local_version
    use_managed_prompt = getattr(observation_sink, "use_managed_prompt", None)
    if callable(use_managed_prompt):
        use_managed_prompt(managed_prompt)
    return rendered_prompt, managed_version


def _context_prompt(context: CoachingContextBundle) -> str:
    from app.schemas.applicant_context import APPLICANT_CONTEXT_GUIDANCE

    payload = context.model_dump(mode="json")
    if context.job_context.supplemental_context:
        payload["job_context"]["supplemental_context"] = context.job_context.supplemental_context
    applicant = context.job_context.applicant_context
    if applicant is not None:
        payload["job_context"]["applicant_context"] = applicant.model_context()
    return (
        (APPLICANT_CONTEXT_GUIDANCE if applicant is not None or context.job_context.supplemental_context else "")
        + "다음은 서버가 MCP로 조회하고 검증한 코칭 문맥입니다. 제공된 ID와 답변 "
        "문장만 사용하세요.\n"
        + json.dumps(payload, ensure_ascii=False)
    )


def _normalize_json_envelope(raw_content: object) -> str:
    """Safely strip markdown code fences from JSON output without extracting arbitrary text."""
    if not isinstance(raw_content, str):
        raise TypeError("message content must be a string")
    stripped = raw_content.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            first_line = lines[0][3:].strip().lower()
            if first_line in ("", "json"):
                inner = "\n".join(lines[1:-1]).strip()
                if inner:
                    return inner
    return stripped


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None


def _cache_usage_value(payload: object, key: str) -> int | None:
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    details = usage.get("prompt_tokens_details")
    if not isinstance(details, dict):
        return None
    return _optional_int(details.get(key))


def _usage_from_payload(
    payload: dict[str, object],
) -> tuple[int | None, int | None, float | None]:
    usage = payload.get("usage", {})
    if not isinstance(usage, dict):
        return None, None, None
    return (
        _optional_int(usage.get("prompt_tokens", usage.get("input_tokens"))),
        _optional_int(
            usage.get("completion_tokens", usage.get("output_tokens"))
        ),
        _optional_float(usage.get("cost")),
    )


def _strict_json_schema(schema: dict[str, object]) -> dict[str, object]:
    """OpenAI strict output requires every object property to be required."""

    normalized = deepcopy(schema)

    def visit(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["required"] = list(properties)
                node["additionalProperties"] = False
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(normalized)
    return normalized


def build_coaching_service_from_env(
    observation_sink: CoachingObservationSink | Any | None = None,
) -> McpLlmCoachingService | None:
    provider_name = os.getenv("COACHING_PROVIDER", "").strip().lower()
    model_name = os.getenv("COACHING_LLM_MODEL", "").strip() or os.getenv(
        "COACHING_MODEL", ""
    ).strip()
    if provider_name == "ollama":
        api_key = os.getenv("COACHING_LLM_API_KEY", "").strip() or "ollama"
        base_url = os.getenv(
            "COACHING_OLLAMA_URL", "http://127.0.0.1:11434"
        ).strip().rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        default_timeout = "180"
    else:
        api_key = os.getenv("COACHING_LLM_API_KEY", "").strip() or os.getenv(
            "OPENROUTER_API_KEY", ""
        ).strip()
        base_url = os.getenv(
            "COACHING_LLM_BASE_URL", "https://openrouter.ai/api/v1"
        )
        default_timeout = "25"
    mcp_secret = os.getenv("MCP_INTERNAL_SECRET", "").strip()
    if not api_key or not model_name or len(mcp_secret) < 32:
        return None
    prompt_text, prompt_version = load_managed_coaching_prompt(observation_sink)
    skill_version = os.getenv(
        "COACHING_SKILL_VERSION", DEFAULT_SKILL_VERSION
    ).strip() or DEFAULT_SKILL_VERSION
    try:
        settings = SupabaseSettings.from_env(require_service_role=True)
        run_repository = SupabaseCoachingRunRepository(settings)
        codec = McpAccessTokenCodec(mcp_secret)
    except (SupabaseSettingsError, ValueError):
        return None
    try:
        timeout_seconds = float(
            os.getenv("COACHING_LLM_TIMEOUT_SECONDS", "").strip()
            or default_timeout
        )
        max_transport_attempts = int(
            os.getenv("COACHING_LLM_MAX_TRANSPORT_ATTEMPTS", "2").strip()
        )
        backoff_seconds = float(
            os.getenv("COACHING_LLM_BACKOFF_SECONDS", "0.5").strip()
        )
        max_backoff_seconds = float(
            os.getenv("COACHING_LLM_MAX_BACKOFF_SECONDS", "2.0").strip()
        )
        max_cost_usd = float(
            os.getenv("COACHING_LLM_MAX_COST_USD", "0.10").strip()
        )
        provider = OpenAICompatibleJsonProvider(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_transport_attempts=max_transport_attempts,
            backoff_seconds=backoff_seconds,
            max_backoff_seconds=max_backoff_seconds,
            observation_sink=observation_sink,
            prompt_version=prompt_version,
            skill_version=skill_version,
            require_provider_parameters=(
                os.getenv("OPENROUTER_REQUIRE_PARAMETERS", "true").strip().casefold()
                not in {"0", "false", "no", "off"}
            ),
        )
    except ValueError:
        return None
    return McpLlmCoachingService(
        McpStdioContextGateway(codec),
        provider,
        run_repository=run_repository,
        max_cost_usd=max_cost_usd,
        observation_sink=observation_sink,
        system_prompt=prompt_text,
        prompt_version=prompt_version,
    )
