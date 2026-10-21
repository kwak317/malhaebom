"""API 실패를 클라이언트가 일관되게 처리하기 위한 공통 계약."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class FailureState(StrEnum):
    SCHEMA_VIOLATION = "schema_violation"
    AUTH_ERROR = "auth_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CONTEXT_ERROR = "context_error"
    MCP_ERROR = "mcp_error"
    PROVIDER_ERROR = "provider_error"


class ApiErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: FailureState
    code: str
    message: str
    retryable: bool


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: ApiErrorDetail


def api_error_detail(
    *,
    state: FailureState,
    code: str,
    message: str,
    retryable: bool,
) -> dict[str, object]:
    """FastAPI ``HTTPException.detail``에 넣을 JSON 안전 payload를 만든다."""

    return ApiErrorDetail(
        state=state,
        code=code,
        message=message,
        retryable=retryable,
    ).model_dump(mode="json")
