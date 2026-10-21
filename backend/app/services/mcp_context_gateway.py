from __future__ import annotations

import asyncio
from contextvars import ContextVar
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.core.auth import AuthenticatedUser
from app.schemas.coaching import (
    CoachingAnalyzeRequest,
    CoachingContextBundle,
    JobContext,
    PracticeAttemptContext,
    QuestionContext,
)
from app.services.mcp_access import McpAccessTokenCodec


class McpContextGatewayError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "COACHING_MCP_UNAVAILABLE",
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


_mcp_tool_names: ContextVar[list[str] | None] = ContextVar("mcp_tool_names", default=None)


def begin_mcp_observation():
    return _mcp_tool_names.set([])


def reset_mcp_observation(token) -> None:
    _mcp_tool_names.reset(token)


def observed_mcp_tool_names() -> tuple[str, ...]:
    return tuple(_mcp_tool_names.get() or ())


class McpStdioContextGateway:
    """FastAPI에서 별도 FastMCP 프로세스의 제한된 도구를 실제 호출한다."""

    def __init__(
        self,
        token_codec: McpAccessTokenCodec,
        *,
        server_script: Path | None = None,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.token_codec = token_codec
        configured_server_script = os.getenv("MCP_SERVER_SCRIPT", "").strip()
        self.server_script = server_script or (
            Path(configured_server_script)
            if configured_server_script
            else Path(__file__).resolve().parents[3] / "mcp_server" / "server.py"
        )
        self.timeout_seconds = timeout_seconds

    def load_context(
        self, user: AuthenticatedUser, request: CoachingAnalyzeRequest
    ) -> CoachingContextBundle:
        context_token = self.token_codec.issue(
            user_id=user.user_id,
            request=request,
        )
        try:
            context, tool_names = asyncio.run(
                asyncio.wait_for(
                    self._load_context(context_token, user.user_id, request),
                    timeout=self.timeout_seconds,
                )
            )
            observed = _mcp_tool_names.get()
            if observed is not None:
                observed.extend(tool_names)
            return context
        except McpContextGatewayError:
            raise
        except asyncio.TimeoutError as error:
            raise McpContextGatewayError(
                "MCP 코칭 문맥 조회 시간이 초과되었습니다.",
                code="COACHING_MCP_TIMEOUT",
                retryable=True,
            ) from error
        except Exception as error:
            raise McpContextGatewayError(
                "MCP 코칭 문맥을 불러오지 못했습니다.",
                code="COACHING_MCP_UNAVAILABLE",
                retryable=True,
            ) from error

    async def _load_context(
        self,
        context_token: str,
        user_id: str,
        request: CoachingAnalyzeRequest,
    ) -> tuple[CoachingContextBundle, tuple[str, ...]]:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_script)],
            env=dict(os.environ),
        )
        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                question_result, attempt_result, job_result = await asyncio.gather(
                    session.call_tool(
                        "get_question",
                        {
                            "context_token": context_token,
                            "question_id": request.question_id,
                        },
                    ),
                    session.call_tool(
                        "get_practice_attempt",
                        {
                            "context_token": context_token,
                            "answer_revision_id": str(request.answer_revision_id),
                        },
                    ),
                    session.call_tool(
                        "get_job_context",
                        {
                            "context_token": context_token,
                            "job_snapshot_id": str(request.job_snapshot_id),
                        },
                    ),
                )
        practice_attempt = _tool_payload(attempt_result)
        practice_attempt["user_id"] = user_id
        job_context = _tool_payload(job_result)
        job_context["user_id"] = user_id
        return CoachingContextBundle(
            question=QuestionContext.model_validate(_tool_payload(question_result)),
            practice_attempt=PracticeAttemptContext.model_validate(practice_attempt),
            job_context=JobContext.model_validate(job_context),
        ), ("get_question", "get_practice_attempt", "get_job_context")


def _tool_payload(result: Any) -> dict[str, object]:
    if getattr(result, "isError", False):
        raise McpContextGatewayError(
            "MCP 도구가 코칭 문맥을 거절했습니다.",
            code="COACHING_MCP_TOOL_ERROR",
            retryable=True,
        )
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if not isinstance(text, str):
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise McpContextGatewayError(
        "MCP 도구 응답 형식을 확인하지 못했습니다.",
        code="COACHING_MCP_INVALID_RESPONSE",
        retryable=False,
    )
