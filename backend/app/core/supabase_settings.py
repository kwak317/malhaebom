from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


class SupabaseSettingsError(RuntimeError):
    pass


def is_allowed_supabase_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.netloc:
        return True
    return parsed.scheme == "http" and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "host.docker.internal",
    }


@dataclass(frozen=True)
class SupabaseSettings:
    url: str
    publishable_key: str
    service_role_key: str | None = None

    @classmethod
    def from_env(cls, require_service_role: bool = False) -> "SupabaseSettings":
        url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None
        if not is_allowed_supabase_url(url):
            raise SupabaseSettingsError(
                "SUPABASE_URL은 https URL이어야 하며 로컬 개발 주소만 http를 허용합니다."
            )
        if not publishable_key:
            raise SupabaseSettingsError("SUPABASE_PUBLISHABLE_KEY 환경변수가 필요합니다.")
        if require_service_role and not service_role_key:
            raise SupabaseSettingsError("SUPABASE_SERVICE_ROLE_KEY 환경변수가 필요합니다.")
        return cls(url, publishable_key, service_role_key)
