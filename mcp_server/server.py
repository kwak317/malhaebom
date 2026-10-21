"""말해봄 코칭 문맥을 읽는 제한된 FastMCP 서버."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from uuid import UUID


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from mcp.server.auth.middleware.auth_context import get_access_token  # noqa: E402
from mcp.server.auth.provider import AccessToken, TokenVerifier  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402

from app.core.auth import (  # noqa: E402
    AuthConfigurationError,
    AuthenticatedUser,
    InvalidAccessToken,
    build_access_token_verifier_from_env,
)
from app.services.attempt_comparison import (  # noqa: E402
    AttemptComparisonService,
    build_demo_attempt_comparison_service,
)
from app.services.coaching_context import (  # noqa: E402
    CoachingContextService,
    build_demo_coaching_service,
)
from app.services.mcp_access import (  # noqa: E402
    MCP_COMPARISON_READ_SCOPE,
    MCP_READ_SCOPES,
    McpAccessDenied,
    McpAccessClaims,
    McpComparisonAccessClaims,
    McpAccessTokenCodec,
)
from app.services.supabase_attempt_comparison import (  # noqa: E402
    build_supabase_attempt_comparison_service,
)
from app.services.supabase_coaching_context import (  # noqa: E402
    build_supabase_coaching_context_service,
)


class McpConfigurationError(RuntimeError):
    pass


class McpHttpTokenVerifier(TokenVerifier):
    """기존 FastAPI 사용자 token verifier를 MCP SDK 인증 계약에 연결한다."""

    def __init__(self, verifier: Any | None = None) -> None:
        self.verifier = verifier

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            if self.verifier is None:
                self.verifier = build_access_token_verifier_from_env()
            verifier = self.verifier
            user_id = verifier.verify_access_token(token)
        except (AuthConfigurationError, InvalidAccessToken):
            return None
        return AccessToken(
            token=token,
            client_id=f"malhaebom-user:{user_id}",
            subject=user_id,
            scopes=list(MCP_READ_SCOPES),
        )


mcp = FastMCP(
    "malhaebom-context",
    instructions=(
        "서버가 허용한 질문·현재 답변·공고 문맥만 읽습니다. "
        "원문 검색, 임의 SQL과 임의 URL 호출은 제공하지 않습니다."
    ),
)

_context_service: CoachingContextService | None = None
_comparison_service: AttemptComparisonService | None = None
_token_codec: McpAccessTokenCodec | None = None


def configure_mcp_dependencies(
    *,
    context_service: CoachingContextService | None,
    token_codec: McpAccessTokenCodec | None,
    comparison_service: AttemptComparisonService | None = None,
) -> None:
    """테스트나 서버 bootstrap이 명시적 의존성을 주입한다."""

    global _context_service, _comparison_service, _token_codec
    _context_service = context_service
    _comparison_service = comparison_service
    _token_codec = token_codec


def _resolve_access(
    context_token: str,
) -> tuple[McpAccessClaims, AuthenticatedUser, CoachingContextService]:
    codec = _token_codec
    if codec is None:
        secret = os.getenv("MCP_INTERNAL_SECRET", "")
        if not secret:
            raise McpConfigurationError("MCP_INTERNAL_SECRET 환경변수가 필요합니다.")
        codec = McpAccessTokenCodec(secret)

    claims = codec.verify(context_token)
    access_token = get_access_token()
    if access_token is not None and access_token.subject != claims.user_id:
        raise McpAccessDenied()
    user = AuthenticatedUser(user_id=claims.user_id, access_token="")
    service = _context_service
    if service is None:
        mock_enabled = os.getenv("COACHING_MOCK_ENABLED", "false").strip().lower()
        if mock_enabled in {"1", "true", "yes"}:
            service = build_demo_coaching_service(claims.user_id).context_service
        else:
            service = build_supabase_coaching_context_service()
    return claims, user, service


def _resolve_comparison_access(
    context_token: str,
) -> tuple[
    McpComparisonAccessClaims,
    AuthenticatedUser,
    AttemptComparisonService,
]:
    codec = _token_codec
    if codec is None:
        secret = os.getenv("MCP_INTERNAL_SECRET", "")
        if not secret:
            raise McpConfigurationError("MCP_INTERNAL_SECRET 환경변수가 필요합니다.")
        codec = McpAccessTokenCodec(secret)

    claims = codec.verify_comparison(context_token)
    access_token = get_access_token()
    if access_token is not None and access_token.subject != claims.user_id:
        raise McpAccessDenied()
    user = AuthenticatedUser(user_id=claims.user_id, access_token="")
    service = _comparison_service
    if service is None:
        mock_enabled = os.getenv("COACHING_MOCK_ENABLED", "false").strip().lower()
        if mock_enabled in {"1", "true", "yes"}:
            service = build_demo_attempt_comparison_service(claims.user_id)
        else:
            service = build_supabase_attempt_comparison_service()
    return claims, user, service


@mcp.tool()
def get_question(context_token: str, question_id: str) -> dict[str, object]:
    """허용된 현재 답변과 연결된 고정 질문·유형·활성 기준을 읽습니다.

    Args:
        context_token: FastAPI가 숨은 인수로 전달하는 짧은 내부 토큰
        question_id: 서버 토큰이 허용한 질문 ID
    """

    claims, user, service = _resolve_access(context_token)
    claims.require_scope("question:read")
    claims.require_question(question_id)
    result = service.get_question(
        user,
        question_id=question_id,
        answer_revision_id=claims.answer_revision_id,
    )
    return result.model_dump(mode="json")


@mcp.tool()
def get_practice_attempt(
    context_token: str, answer_revision_id: str
) -> dict[str, object]:
    """허용된 사용자의 확인된 현재 답변 문장·전달력·만료를 읽습니다.

    Args:
        context_token: FastAPI가 숨은 인수로 전달하는 짧은 내부 토큰
        answer_revision_id: 서버 토큰이 허용한 답변 revision UUID
    """

    claims, user, service = _resolve_access(context_token)
    try:
        revision_id = UUID(answer_revision_id)
    except ValueError as error:
        raise McpAccessDenied() from error
    claims.require_scope("practice_attempt:read")
    claims.require_answer_revision(revision_id)
    result = service.get_practice_attempt(
        user,
        answer_revision_id=revision_id,
    )
    return result.model_dump(mode="json", exclude={"user_id"})


@mcp.tool()
def get_job_context(
    context_token: str, job_snapshot_id: str
) -> dict[str, object]:
    """허용된 연습 세션에 고정된 검토 공고와 선택 요구사항을 읽습니다.

    Args:
        context_token: FastAPI가 숨은 인수로 전달하는 짧은 내부 토큰
        job_snapshot_id: 서버 토큰이 허용한 공고 snapshot UUID
    """

    claims, user, service = _resolve_access(context_token)
    try:
        snapshot_id = UUID(job_snapshot_id)
    except ValueError as error:
        raise McpAccessDenied() from error
    claims.require_scope("job_context:read")
    claims.require_job_snapshot(snapshot_id)
    result = service.get_job_context(
        user,
        job_snapshot_id=snapshot_id,
        answer_revision_id=claims.answer_revision_id,
    )
    return result.model_dump(mode="json", exclude={"user_id"})


@mcp.tool()
def compare_attempts(
    context_token: str,
    previous_coaching_run_id: str,
    current_coaching_run_id: str,
) -> dict[str, object]:
    """저장된 1차·2차 코칭 결과를 추가 LLM 호출 없이 비교합니다.

    Args:
        context_token: FastAPI가 숨은 인수로 전달하는 짧은 내부 토큰
        previous_coaching_run_id: 토큰이 허용한 1차 코칭 결과 UUID
        current_coaching_run_id: 토큰이 허용한 2차 코칭 결과 UUID
    """

    claims, user, service = _resolve_comparison_access(context_token)
    try:
        previous_run_id = UUID(previous_coaching_run_id)
        current_run_id = UUID(current_coaching_run_id)
    except ValueError as error:
        raise McpAccessDenied() from error
    claims.require_scope(MCP_COMPARISON_READ_SCOPE)
    claims.require_run_pair(previous_run_id, current_run_id)
    return service.compare(
        user,
        previous_coaching_run_id=previous_run_id,
        current_coaching_run_id=current_run_id,
    )


def create_http_mcp_server(
    access_token_verifier: Any | None = None,
    *,
    issuer_url: str | None = None,
    resource_server_url: str | None = None,
) -> FastMCP:
    """FastAPI에 mount할 인증된 stateless Streamable HTTP 서버를 만든다."""

    configured_issuer = issuer_url or os.getenv("MCP_AUTH_ISSUER_URL", "").strip()
    if not configured_issuer:
        supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        configured_issuer = (
            f"{supabase_url}/auth/v1"
            if supabase_url
            else "http://localhost:8000"
        )
    configured_resource = (
        resource_server_url
        or os.getenv("MCP_RESOURCE_SERVER_URL", "").strip()
        or "http://localhost:8000/mcp"
    )
    server = FastMCP(
        "malhaebom-context-http",
        instructions=mcp.instructions,
        token_verifier=McpHttpTokenVerifier(access_token_verifier),
        auth=AuthSettings(
            issuer_url=configured_issuer,
            resource_server_url=configured_resource,
            required_scopes=list(MCP_READ_SCOPES),
            # Supabase access token의 audience는 `authenticated`이며 URL resource가 아니다.
            validate_token_resource=False,
        ),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
    server.tool()(get_question)
    server.tool()(get_practice_attempt)
    server.tool()(get_job_context)
    server.tool()(compare_attempts)
    return server


if __name__ == "__main__":
    mcp.run()
