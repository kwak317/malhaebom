"""준비 대화 생성 실패 복구. 상태 변경 없이 JSON/스키마 실패에만 한 번 재시도한다."""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Callable

from pydantic import ValidationError
from app.schemas.preparation_conversation import PreparationConversationOutput

GENERATION_FAILURE_MESSAGE = "응답을 확인하지 못했어요. 현재 내용은 유지했으니 다시 보내기 버튼으로 시도해 주세요."


@dataclass(frozen=True)
class PreparationGenerationAttempt:
    provider_response: dict[str, Any] | None
    output: dict[str, Any] | None
    error: str | None
    latency_seconds: float
    http_status: int | None = None


@dataclass(frozen=True)
class PreparationGenerationResult:
    attempts: tuple[PreparationGenerationAttempt, ...]

    @property
    def output(self) -> dict[str, Any] | None:
        return self.attempts[-1].output

    @property
    def recovered(self) -> bool:
        return len(self.attempts) == 2 and self.output is not None

    @property
    def failure_message(self) -> str | None:
        return GENERATION_FAILURE_MESSAGE if self.output is None else None


def generate_preparation_response(generate: Callable[[], dict[str, Any]]) -> PreparationGenerationResult:
    """generate는 같은 Prompt·문맥으로 모델만 호출한다. DB/진행 작업을 넣지 않는다.

    전송·공급자 예외와 의미/정책 오류는 자동 재시도하지 않는다. 출력 한도 초과,
    JSON 파싱 또는 구조 스키마 실패에만 한 번 추가 호출하며 원본을 모두 보존한다.
    """
    attempts = []
    for _ in range(2):
        start = time.perf_counter()
        raw = None
        try:
            raw = generate()
        except Exception as error:
            attempts.append(PreparationGenerationAttempt(None, None, type(error).__name__, time.perf_counter()-start, getattr(error, "status_code", None)))
            break
        try:
            choice = raw["choices"][0]
            if choice.get("finish_reason") == "length":
                code = "truncated_output"
                output = None
            else:
                output = json.loads(choice["message"]["content"] or "")
                PreparationConversationOutput.model_validate(output)
                code = None
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            code, output = "invalid_JSON", None
        except ValidationError:
            code, output = "invalid_output_schema", None
        attempts.append(PreparationGenerationAttempt(raw, output, code, time.perf_counter()-start))
        if output is not None:
            break
    return PreparationGenerationResult(tuple(attempts))


def preparation_output_schema(context):
    """출처 ID는 서버가 제공한 값만 생성하도록 공급자 계약에도 고정한다."""
    schema = PreparationConversationOutput.model_json_schema()
    ids = list(dict.fromkeys(item["message_id"] for item in context.get("source_messages", [])))
    if ids:
        schema["$defs"]["ExperienceFact"]["properties"]["source_message_id"]["enum"] = ids
    pending = context.get("pending_profile_update") or {}
    properties = schema["$defs"]["ProfileUpdate"]["properties"]
    for field in ("draft_id", "draft_version"):
        if pending.get(field) is not None:
            for branch in properties[field]["anyOf"]:
                if branch.get("type") != "null":
                    branch["enum"] = [pending[field]]
    return schema
