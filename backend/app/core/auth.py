from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.schemas.errors import FailureState, api_error_detail
from app.core.supabase_settings import is_allowed_supabase_url


class AuthConfigurationError(RuntimeError):
    """Raised when the backend cannot verify Supabase access tokens safely."""


class InvalidAccessToken(ValueError):
    """Raised for an absent, expired, or unverifiable Supabase access token."""


class DevelopmentAccessTokenVerifier:
    """명시적으로 켠 Compose E2E에서만 쓰는 고정 토큰 verifier."""

    def __init__(self, token: str, user_id: str = "compose-e2e-user") -> None:
        if len(token) < 16:
            raise AuthConfigurationError("COACHING_E2E_TOKEN은 16자 이상이어야 합니다.")
        self.token = token
        self.user_id = user_id

    def verify_access_token(self, token: str) -> str:
        if token != self.token:
            raise InvalidAccessToken()
        return self.user_id


@dataclass(frozen=True)
class AuthenticatedUser:
    """Verified identity and the short-lived token used for Supabase RLS calls."""

    user_id: str
    access_token: str


class SupabaseJwtVerifier:
    def __init__(
        self,
        supabase_url: str,
        jwks_client: Any | None = None,
        issuer: str | None = None,
    ) -> None:
        normalized_url = supabase_url.strip().rstrip("/")
        if not is_allowed_supabase_url(normalized_url):
            raise AuthConfigurationError(
                "SUPABASE_URL은 https URL이어야 하며 로컬 개발 주소만 http를 허용합니다."
            )

        self.supabase_url = normalized_url
        normalized_issuer = (issuer or f"{self.supabase_url}/auth/v1").strip().rstrip("/")
        if not is_allowed_supabase_url(normalized_issuer):
            raise AuthConfigurationError(
                "SUPABASE_JWT_ISSUER는 https URL이어야 하며 로컬 개발 주소만 http를 허용합니다."
            )

        self.issuer = normalized_issuer
        self.jwks_client = jwks_client or PyJWKClient(
            f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
        )

    @classmethod
    def from_env(cls) -> "SupabaseJwtVerifier":
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        if not supabase_url:
            raise AuthConfigurationError("SUPABASE_URL 환경변수가 필요합니다.")
        issuer = os.getenv("SUPABASE_JWT_ISSUER", "").strip() or None
        return cls(supabase_url, issuer=issuer)

    def verify_access_token(self, token: str) -> str:
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
                issuer=self.issuer,
            )
        except (InvalidTokenError, PyJWKClientError, ValueError) as error:
            raise InvalidAccessToken() from error

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise InvalidAccessToken()
        return subject


def build_access_token_verifier_from_env() -> SupabaseJwtVerifier | DevelopmentAccessTokenVerifier:
    """운영 Supabase verifier 또는 격리된 Compose E2E verifier를 만든다."""

    e2e_enabled = os.getenv("COACHING_E2E_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if not e2e_enabled:
        return SupabaseJwtVerifier.from_env()

    mock_enabled = os.getenv("COACHING_MOCK_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    token = os.getenv("COACHING_E2E_TOKEN", "").strip()
    if not mock_enabled:
        raise AuthConfigurationError(
            "COACHING_E2E_ENABLED는 COACHING_MOCK_ENABLED=true에서만 사용할 수 있습니다."
        )
    return DevelopmentAccessTokenVerifier(token)


def create_require_authenticated_user(
    verifier: SupabaseJwtVerifier | DevelopmentAccessTokenVerifier | Any | None = None,
) -> Callable[..., AuthenticatedUser]:
    active_verifier = verifier

    def require_authenticated_user(
        authorization: str | None = Header(default=None),
    ) -> AuthenticatedUser:
        nonlocal active_verifier
        if not authorization or not authorization.startswith("Bearer "):
            raise _unauthorized()

        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            raise _unauthorized()

        try:
            if active_verifier is None:
                active_verifier = build_access_token_verifier_from_env()
            user_id = active_verifier.verify_access_token(token)
            return AuthenticatedUser(user_id=user_id, access_token=token)
        except (AuthConfigurationError, InvalidAccessToken):
            raise _unauthorized()

    return require_authenticated_user


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=api_error_detail(
            state=FailureState.AUTH_ERROR,
            code="UNAUTHORIZED",
            message="로그인이 필요하거나 세션이 만료되었습니다.",
            retryable=False,
        ),
    )
