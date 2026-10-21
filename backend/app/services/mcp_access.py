"""FastAPI가 MCP 읽기 도구에 전달하는 짧은 내부 토큰."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from app.schemas.coaching import CoachingAnalyzeRequest


MCP_ISSUER = "malhaebom-api"
MCP_AUDIENCE = "malhaebom-mcp"
MCP_CONTEXT_READ_SCOPES = (
    "question:read",
    "practice_attempt:read",
    "job_context:read",
)
MCP_COMPARISON_READ_SCOPE = "attempt_comparison:read"
MCP_READ_SCOPES = (*MCP_CONTEXT_READ_SCOPES, MCP_COMPARISON_READ_SCOPE)
MAX_MCP_TOKEN_TTL_SECONDS = 300


class McpAccessDenied(ValueError):
    """서명·만료·scope·허용 ID가 유효하지 않은 내부 요청."""


@dataclass(frozen=True)
class McpAccessClaims:
    user_id: str
    question_id: str
    answer_revision_id: UUID
    job_snapshot_id: UUID
    scopes: tuple[str, ...]
    expires_at: datetime

    def require_scope(self, scope: str) -> None:
        if scope not in self.scopes:
            raise McpAccessDenied()

    def require_question(self, question_id: str) -> None:
        if self.question_id != question_id:
            raise McpAccessDenied()

    def require_answer_revision(self, answer_revision_id: UUID) -> None:
        if self.answer_revision_id != answer_revision_id:
            raise McpAccessDenied()

    def require_job_snapshot(self, job_snapshot_id: UUID) -> None:
        if self.job_snapshot_id != job_snapshot_id:
            raise McpAccessDenied()


@dataclass(frozen=True)
class McpComparisonAccessClaims:
    user_id: str
    previous_coaching_run_id: UUID
    current_coaching_run_id: UUID
    scopes: tuple[str, ...]
    expires_at: datetime

    def require_scope(self, scope: str) -> None:
        if scope not in self.scopes:
            raise McpAccessDenied()

    def require_run_pair(
        self,
        previous_coaching_run_id: UUID,
        current_coaching_run_id: UUID,
    ) -> None:
        if (
            self.previous_coaching_run_id != previous_coaching_run_id
            or self.current_coaching_run_id != current_coaching_run_id
        ):
            raise McpAccessDenied()


class McpAccessTokenCodec:
    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise ValueError("MCP 내부 토큰 secret은 32자 이상이어야 합니다.")
        self.secret = secret

    def issue(
        self,
        *,
        user_id: str,
        request: CoachingAnalyzeRequest,
        ttl_seconds: int = 60,
        now: datetime | None = None,
    ) -> str:
        if not user_id.strip() or not 1 <= ttl_seconds <= MAX_MCP_TOKEN_TTL_SECONDS:
            raise ValueError("MCP 내부 토큰 사용자와 TTL을 확인해 주세요.")
        issued_at = now or datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=ttl_seconds)
        return jwt.encode(
            {
                "iss": MCP_ISSUER,
                "aud": MCP_AUDIENCE,
                "sub": user_id,
                "iat": int(issued_at.timestamp()),
                "exp": int(expires_at.timestamp()),
                "scope": list(MCP_CONTEXT_READ_SCOPES),
                "question_id": request.question_id,
                "answer_revision_id": str(request.answer_revision_id),
                "job_snapshot_id": str(request.job_snapshot_id),
            },
            self.secret,
            algorithm="HS256",
        )

    def issue_comparison(
        self,
        *,
        user_id: str,
        previous_coaching_run_id: UUID,
        current_coaching_run_id: UUID,
        ttl_seconds: int = 60,
        now: datetime | None = None,
    ) -> str:
        if (
            not user_id.strip()
            or previous_coaching_run_id == current_coaching_run_id
            or not 1 <= ttl_seconds <= MAX_MCP_TOKEN_TTL_SECONDS
        ):
            raise ValueError("MCP 비교 토큰 사용자·결과 ID·TTL을 확인해 주세요.")
        issued_at = now or datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=ttl_seconds)
        return jwt.encode(
            {
                "iss": MCP_ISSUER,
                "aud": MCP_AUDIENCE,
                "sub": user_id,
                "iat": int(issued_at.timestamp()),
                "exp": int(expires_at.timestamp()),
                "scope": [MCP_COMPARISON_READ_SCOPE],
                "previous_coaching_run_id": str(previous_coaching_run_id),
                "current_coaching_run_id": str(current_coaching_run_id),
            },
            self.secret,
            algorithm="HS256",
        )

    def verify(
        self, token: str, *, now: datetime | None = None
    ) -> McpAccessClaims:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                audience=MCP_AUDIENCE,
                issuer=MCP_ISSUER,
                options={
                    "verify_exp": False,
                    "require": [
                        "iss",
                        "aud",
                        "sub",
                        "iat",
                        "exp",
                        "scope",
                        "question_id",
                        "answer_revision_id",
                        "job_snapshot_id",
                    ],
                },
            )
            expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
            active_now = now or datetime.now(UTC)
            scopes = tuple(str(item) for item in payload["scope"])
            if expires_at <= active_now or not set(scopes).issubset(
                MCP_CONTEXT_READ_SCOPES
            ):
                raise McpAccessDenied()
            user_id = str(payload["sub"]).strip()
            question_id = str(payload["question_id"]).strip()
            if not user_id or not question_id:
                raise McpAccessDenied()
            return McpAccessClaims(
                user_id=user_id,
                question_id=question_id,
                answer_revision_id=UUID(str(payload["answer_revision_id"])),
                job_snapshot_id=UUID(str(payload["job_snapshot_id"])),
                scopes=scopes,
                expires_at=expires_at,
            )
        except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
            if isinstance(error, McpAccessDenied):
                raise
            raise McpAccessDenied() from error

    def verify_comparison(
        self, token: str, *, now: datetime | None = None
    ) -> McpComparisonAccessClaims:
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                audience=MCP_AUDIENCE,
                issuer=MCP_ISSUER,
                options={
                    "verify_exp": False,
                    "require": [
                        "iss",
                        "aud",
                        "sub",
                        "iat",
                        "exp",
                        "scope",
                        "previous_coaching_run_id",
                        "current_coaching_run_id",
                    ],
                },
            )
            expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
            active_now = now or datetime.now(UTC)
            scopes = tuple(str(item) for item in payload["scope"])
            if expires_at <= active_now or set(scopes) != {MCP_COMPARISON_READ_SCOPE}:
                raise McpAccessDenied()
            user_id = str(payload["sub"]).strip()
            previous_run_id = UUID(str(payload["previous_coaching_run_id"]))
            current_run_id = UUID(str(payload["current_coaching_run_id"]))
            if not user_id or previous_run_id == current_run_id:
                raise McpAccessDenied()
            return McpComparisonAccessClaims(
                user_id=user_id,
                previous_coaching_run_id=previous_run_id,
                current_coaching_run_id=current_run_id,
                scopes=scopes,
                expires_at=expires_at,
            )
        except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
            if isinstance(error, McpAccessDenied):
                raise
            raise McpAccessDenied() from error
