"""개인정보를 남기지 않는 코칭 Langfuse 관측 계약."""

from __future__ import annotations

import hashlib
import hmac
import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.errors import FailureState
from app.services.coaching_diagnostics import CoachingAttemptFailure, ErrorCode, FailureStage
from app.services.coaching_prompt import DEFAULT_COACHING_PROMPT_VERSION
from app.services.coaching_skill import load_skill_bundle


COACHING_TRACE_NAME = "coaching.analyze"
DEFAULT_PROMPT_VERSION = DEFAULT_COACHING_PROMPT_VERSION
DEFAULT_SKILL_VERSION = load_skill_bundle().catalog.skill_version
FORBIDDEN_OBSERVATION_KEYS = frozenset(
    {
        "access_token",
        "answer",
        "answer_segments",
        "authorization",
        "evidence",
        "job_posting",
        "quote",
        "raw_input",
        "raw_output",
        "source_url",
        "transcript",
    }
)


class CoachingObservation(BaseModel):
    """Langfuse에 허용하는 최소 집계 필드."""

    model_config = ConfigDict(extra="forbid")

    trace_name: str = COACHING_TRACE_NAME
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    user_key: str | None = None
    session_key: str | None = None
    model: str
    prompt_version: str
    skill_version: str
    status: str | None = None
    latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    failure_state: FailureState | None = None
    failure_stage: FailureStage | None = None
    error_code: ErrorCode | None = None
    attempt_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    attempt_failures: list[CoachingAttemptFailure] = Field(default_factory=list)
    criterion_count: int = Field(default=0, ge=0)
    gap_count: int = Field(default=0, ge=0)


class CoachingGenerationObservation(BaseModel):
    """원문 없이 provider HTTP 시도 한 번을 나타낸다."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    generation_id: str = Field(default_factory=lambda: uuid4().hex)
    model: str
    prompt_version: str
    skill_version: str
    contract_attempt: int = Field(ge=1)
    transport_attempt: int = Field(ge=1)
    repair_prompt: bool = False
    status_code: int | None = Field(default=None, ge=100, le=599)
    outcome: str
    retry_reason: str | None = None
    will_retry: bool = False
    latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    output_is_json_object: bool = False
    cached_input_tokens: int | None = Field(default=None, ge=0)
    cache_write_tokens: int | None = Field(default=None, ge=0)
    cached_system_hash: str | None = None


class CoachingValidationObservation(BaseModel):
    """모델 출력의 Pydantic·서버 참조 검증 한 번을 나타낸다."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    span_id: str = Field(default_factory=lambda: uuid4().hex)
    prompt_version: str
    skill_version: str
    contract_attempt: int = Field(ge=1)
    valid: bool
    error_count: int = Field(ge=0)
    latency_ms: float = Field(ge=0)


@dataclass
class CoachingTraceContext:
    trace_id: str
    user_key: str | None = None
    session_key: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    has_input_tokens: bool = False
    has_output_tokens: bool = False
    has_cost: bool = False

    def add_usage(self, observation: CoachingGenerationObservation) -> None:
        if observation.input_tokens is not None:
            self.input_tokens += observation.input_tokens
            self.has_input_tokens = True
        if observation.output_tokens is not None:
            self.output_tokens += observation.output_tokens
            self.has_output_tokens = True
        if observation.cost_usd is not None:
            self.cost_usd += observation.cost_usd
            self.has_cost = True


_ACTIVE_COACHING_TRACE: ContextVar[CoachingTraceContext | None] = ContextVar(
    "active_coaching_trace",
    default=None,
)


class CoachingObservationSink(Protocol):
    def record(self, observation: CoachingObservation) -> None: ...

    def record_generation(
        self, observation: CoachingGenerationObservation
    ) -> None: ...

    def start_generation(
        self, observation: CoachingGenerationObservation
    ) -> None: ...

    def record_validation(
        self, observation: CoachingValidationObservation
    ) -> None: ...


class NoopCoachingObservationSink:
    def record(self, observation: CoachingObservation) -> None:
        del observation

    def record_generation(self, observation: CoachingGenerationObservation) -> None:
        del observation

    def start_generation(self, observation: CoachingGenerationObservation) -> None:
        del observation

    def record_validation(self, observation: CoachingValidationObservation) -> None:
        del observation


class LangfuseCoachingObservationSink:
    """Langfuse SDK 호출을 한 곳으로 제한한다."""

    def __init__(self, client: Any, managed_prompt: Any | None = None) -> None:
        self.client = client
        self.managed_prompt = managed_prompt
        self._active_generations: dict[str, Any] = {}

    def use_managed_prompt(self, managed_prompt: Any) -> None:
        self.managed_prompt = managed_prompt

    def record(self, observation: CoachingObservation) -> None:
        payload = observation.model_dump(
            mode="json",
            exclude={"trace_name", "trace_id", "user_key", "session_key"},
        )
        _assert_no_sensitive_keys(payload)
        with _propagate_trace_attributes(
            trace_name=observation.trace_name,
            user_id=observation.user_key,
            session_id=observation.session_key,
            version=observation.prompt_version,
        ):
            span = self.client.start_observation(
                trace_context={"trace_id": observation.trace_id},
                name=observation.trace_name,
                as_type="span",
                version=observation.prompt_version,
                metadata=payload,
                output={
                    "content_policy": "redacted",
                    "status": observation.status,
                },
                level=(
                    "ERROR"
                    if observation.failure_state is not None
                    else "DEFAULT"
                ),
            )
            span.end()

    def record_http_request(self, *, trace_id: str, method: str, path: str,
                            status_code: int, latency_ms: float) -> None:
        # 원문·인증값·쿼리 문자열 없이 요청과 trace의 직접 연결만 기록한다.
        span = self.client.start_observation(
            trace_context={"trace_id": trace_id}, name="http.request", as_type="span",
            metadata={"request_id": trace_id, "method": method, "path": path,
                      "http_status": status_code, "latency_ms": latency_ms},
            level="ERROR" if status_code >= 400 else "DEFAULT",
        )
        span.end()

    def _generation_payload(
        self, observation: CoachingGenerationObservation
    ) -> dict[str, Any]:
        payload = observation.model_dump(
            mode="json",
            exclude={
                "trace_id",
                "generation_id",
                "model",
                "prompt_version",
                "input_tokens",
                "output_tokens",
                "cost_usd",
                "output_is_json_object",
            },
        )
        _assert_no_sensitive_keys(payload)
        usage_details = {
            key: value
            for key, value in {
                "input": observation.input_tokens,
                "output": observation.output_tokens,
            }.items()
            if value is not None
        }
        cost_details = (
            {"total": observation.cost_usd}
            if observation.cost_usd is not None
            else None
        )
        generation_payload: dict[str, Any] = {
            "model": observation.model,
            "version": observation.prompt_version,
            "input": {
                "content_policy": "redacted",
                "message_count": 2,
                "schema_name": "malhaebom_coaching",
                "repair_prompt": observation.repair_prompt,
            },
            "output": {
                "content_policy": "redacted",
                "json_object": observation.output_is_json_object,
            },
            "usage_details": usage_details or None,
            "cost_details": cost_details,
            "metadata": {**payload, "skill_version": observation.skill_version},
            "level": "DEFAULT" if observation.outcome == "success" else "ERROR",
        }
        if self.managed_prompt is not None:
            generation_payload["prompt"] = self.managed_prompt
        return generation_payload

    def start_generation(self, observation: CoachingGenerationObservation) -> None:
        generation_payload = self._generation_payload(observation)
        with _propagate_trace_attributes(
            trace_name=COACHING_TRACE_NAME,
            user_id=(
                active_coaching_trace().user_key
                if active_coaching_trace() is not None
                else None
            ),
            session_id=(
                active_coaching_trace().session_key
                if active_coaching_trace() is not None
                else None
            ),
            version=observation.prompt_version,
        ):
            generation = self.client.start_observation(
                trace_context={"trace_id": observation.trace_id},
                name="coaching.provider",
                as_type="generation",
                **generation_payload,
            )
        self._active_generations[observation.generation_id] = generation

    def record_generation(self, observation: CoachingGenerationObservation) -> None:
        generation = self._active_generations.pop(observation.generation_id, None)
        if generation is not None:
            try:
                generation.update(**self._generation_payload(observation))
            finally:
                generation.end()
            return

        self.start_generation(observation)
        self._active_generations.pop(observation.generation_id).end()

    def record_validation(self, observation: CoachingValidationObservation) -> None:
        payload = observation.model_dump(
            mode="json",
            exclude={"trace_id", "span_id", "valid", "error_count"},
        )
        _assert_no_sensitive_keys(payload)
        with _propagate_trace_attributes(
            trace_name=COACHING_TRACE_NAME,
            user_id=(
                active_coaching_trace().user_key
                if active_coaching_trace() is not None
                else None
            ),
            session_id=(
                active_coaching_trace().session_key
                if active_coaching_trace() is not None
                else None
            ),
            version=observation.prompt_version,
        ):
            span = self.client.start_observation(
                trace_context={"trace_id": observation.trace_id},
                name="coaching.output_validation",
                as_type="span",
                version=observation.prompt_version,
                input={
                    "content_policy": "redacted",
                    "contract": "CoachingLLMOutput",
                },
                output={
                    "content_policy": "redacted",
                    "valid": observation.valid,
                    "error_count": observation.error_count,
                },
                metadata={**payload, "skill_version": observation.skill_version},
                level="DEFAULT" if observation.valid else "WARNING",
            )
            span.end()


@contextmanager
def _propagate_trace_attributes(**kwargs):
    from langfuse import propagate_attributes

    with propagate_attributes(**kwargs):
        yield


def activate_coaching_trace(
    trace_id: str | None = None,
) -> tuple[CoachingTraceContext, Token[CoachingTraceContext | None]]:
    context = CoachingTraceContext(trace_id=trace_id or uuid4().hex)
    return context, _ACTIVE_COACHING_TRACE.set(context)


def reset_coaching_trace(token: Token[CoachingTraceContext | None]) -> None:
    _ACTIVE_COACHING_TRACE.reset(token)


def active_coaching_trace() -> CoachingTraceContext | None:
    return _ACTIVE_COACHING_TRACE.get()


def set_active_coaching_identity(
    *, user_key: str | None, session_key: str | None
) -> None:
    context = active_coaching_trace()
    if context is None:
        return
    context.user_key = user_key
    context.session_key = session_key


def observation_trace_id() -> str:
    context = active_coaching_trace()
    return context.trace_id if context is not None else uuid4().hex


def record_generation_safely(
    sink: CoachingObservationSink | Any | None,
    observation: CoachingGenerationObservation,
) -> None:
    context = active_coaching_trace()
    if context is not None and context.trace_id == observation.trace_id:
        context.add_usage(observation)
    callback = getattr(sink, "record_generation", None)
    if callback is None:
        return
    try:
        callback(observation)
    except Exception:
        return


def start_generation_safely(
    sink: CoachingObservationSink | Any | None,
    observation: CoachingGenerationObservation,
) -> None:
    callback = getattr(sink, "start_generation", None)
    if callback is None:
        return
    try:
        callback(observation)
    except Exception:
        return


def record_validation_safely(
    sink: CoachingObservationSink | Any | None,
    observation: CoachingValidationObservation,
) -> None:
    callback = getattr(sink, "record_validation", None)
    if callback is None:
        return
    try:
        callback(observation)
    except Exception:
        return


def build_coaching_observation_sink_from_env() -> CoachingObservationSink:
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    if not public_key or not secret_key:
        return NoopCoachingObservationSink()

    from langfuse import Langfuse

    return LangfuseCoachingObservationSink(
        Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            base_url=(
                os.getenv("LANGFUSE_BASE_URL", "").strip()
                or os.getenv("LANGFUSE_HOST", "").strip()
                or None
            ),
        )
    )


def observation_identity(value: str) -> str | None:
    """설정된 salt가 있을 때만 사용자·세션 ID를 가명 키로 변환한다."""

    salt = os.getenv("COACHING_OBSERVATION_SALT", "").strip()
    if len(salt) < 16:
        return None
    return hmac.new(
        salt.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]


def _assert_no_sensitive_keys(payload: dict[str, object]) -> None:
    discovered: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                discovered.add(str(key).lower())
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    forbidden = discovered & FORBIDDEN_OBSERVATION_KEYS
    if forbidden:
        raise ValueError(
            "관측 payload에 금지된 필드가 있습니다: " + ", ".join(sorted(forbidden))
        )
