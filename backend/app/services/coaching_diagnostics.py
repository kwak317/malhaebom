"""원문 없이 요청별 실패 지점과 시도 이력을 기록한다."""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


FailureStage = Literal["request", "context", "provider", "parse", "validation", "persistence", "internal"]
ErrorCode = Literal[
    "COACHING_REQUEST_FAILED", "COACHING_CONTEXT_LOAD_FAILED",
    "COACHING_PROVIDER_CALL_FAILED", "COACHING_TIMEOUT",
    "COACHING_PROVIDER_CONNECTION_FAILED", "COACHING_RATE_LIMITED",
    "COACHING_CREDITS_EXHAUSTED", "COACHING_PROVIDER_HTTP_ERROR",
    "COACHING_JSON_PARSE_FAILED", "COACHING_JSON_OBJECT_REQUIRED",
    "COACHING_OUTPUT_VALIDATION_FAILED", "COACHING_RESULT_SAVE_FAILED",
    "COACHING_INTERNAL_ERROR",
]
logger = logging.getLogger(__name__)


class CoachingAttemptFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt: int = Field(ge=1)
    stage: FailureStage
    error_code: ErrorCode


@dataclass
class CoachingDiagnostics:
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    failure_stage: FailureStage | None = None
    error_code: ErrorCode | None = None
    attempt_count: int = 0
    attempt_failures: list[CoachingAttemptFailure] = field(default_factory=list)

    def metadata(self) -> dict[str, object]:
        return {
            "failure_stage": self.failure_stage,
            "error_code": self.error_code,
            "attempt_count": self.attempt_count,
            "retry_count": max(0, self.attempt_count - 1),
            "attempt_failures": self.attempt_failures,
        }


_current: ContextVar[CoachingDiagnostics | None] = ContextVar("coaching_diagnostics", default=None)


@contextmanager
def coaching_diagnostics_scope():
    diagnostics = CoachingDiagnostics()
    token = _current.set(diagnostics)
    try:
        yield diagnostics
    finally:
        _current.reset(token)


def start_coaching_attempt() -> None:
    diagnostics = _current.get()
    if diagnostics is not None:
        diagnostics.attempt_count += 1
        finish_coaching_success()


def finish_coaching_success() -> None:
    diagnostics = _current.get()
    if diagnostics is not None:
        diagnostics.failure_stage = None
        diagnostics.error_code = None


def record_coaching_failure(stage: FailureStage, code: ErrorCode) -> None:
    diagnostics = _current.get()
    attempt = diagnostics.attempt_count if diagnostics is not None else 0
    if diagnostics is not None:
        diagnostics.failure_stage = stage
        diagnostics.error_code = code
        if attempt:
            diagnostics.attempt_failures.append(
                CoachingAttemptFailure(attempt=attempt, stage=stage, error_code=code)
            )
    logger.warning("coaching_failure %s", json.dumps({
        "trace_id": diagnostics.trace_id if diagnostics is not None else None,
        "stage": stage, "error_code": code, "attempt_count": attempt,
    }))


def record_observation_failure(trace_id: str) -> None:
    logger.warning(
        "coaching_observation_failure trace_id=%s stage=observability "
        "error_code=COACHING_OBSERVATION_WRITE_FAILED", trace_id,
    )


@contextmanager
def coaching_step(stage: FailureStage, code: ErrorCode):
    try:
        yield
    except Exception:
        diagnostics = _current.get()
        # provider가 더 구체적인 파싱·통신 오류를 기록했으면 유지한다.
        if diagnostics is None or diagnostics.failure_stage is None:
            record_coaching_failure(stage, code)
        raise
