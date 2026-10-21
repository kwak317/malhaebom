"""Supabase에서 소유·만료 범위로 코칭 비교 대상을 읽는 저장소."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from app.core.supabase_settings import SupabaseSettings
from app.services.attempt_comparison import AttemptComparisonService


RUN_SELECT = (
    "id,user_id,answer_revision_id,job_snapshot_id,status,response,model_name,"
    "prompt_version,skill_version,created_at,expires_at,"
    "answer_revisions!inner(id,user_id,practice_session_id,question_id,"
    "confirmed_text,delivery_metrics,expires_at,"
    "analysis_jobs!inner(attempt_no,status,expires_at))"
)


class AttemptComparisonPersistenceError(RuntimeError):
    pass


class SupabaseAttemptComparisonRepository:
    """MCP 프로세스가 service-role로 읽고 서비스가 소유자를 재검사한다."""

    def __init__(
        self,
        settings: SupabaseSettings,
        http_client: httpx.Client | Any | None = None,
    ) -> None:
        if not settings.service_role_key:
            raise AttemptComparisonPersistenceError(
                "SUPABASE_SERVICE_ROLE_KEY가 필요합니다."
            )
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def get_coaching_runs(
        self,
        *,
        user_id: str,
        previous_coaching_run_id: UUID,
        current_coaching_run_id: UUID,
    ) -> list[dict[str, object]]:
        run_filter = quote(
            f"({previous_coaching_run_id},{current_coaching_run_id})",
            safe="(),-",
        )
        owner_filter = quote(user_id, safe="")
        now_filter = quote(datetime.now(UTC).isoformat(), safe="")
        key = self.settings.service_role_key or ""
        try:
            response = self.http.get(
                f"{self.settings.url}/rest/v1/coaching_runs"
                f"?id=in.{run_filter}&user_id=eq.{owner_filter}"
                f"&expires_at=gt.{now_filter}&select={RUN_SELECT}",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
        except httpx.HTTPError as error:
            raise AttemptComparisonPersistenceError(
                "코칭 비교 저장소에 연결하지 못했습니다."
            ) from error
        if response.status_code != 200:
            raise AttemptComparisonPersistenceError(
                f"코칭 비교 저장소 요청에 실패했습니다. (HTTP {response.status_code})"
            )
        try:
            value = response.json()
        except ValueError as error:
            raise AttemptComparisonPersistenceError(
                "코칭 비교 저장소 응답을 처리하지 못했습니다."
            ) from error
        return value if isinstance(value, list) else []


def build_supabase_attempt_comparison_service() -> AttemptComparisonService:
    settings = SupabaseSettings.from_env(require_service_role=True)
    return AttemptComparisonService(SupabaseAttemptComparisonRepository(settings))
