from __future__ import annotations

from typing import Any

import httpx

from app.core.auth import AuthenticatedUser
from app.core.supabase_settings import SupabaseSettings
from app.schemas.coaching import (
    CoachingAnalyzeRequest,
    CoachingContextBundle,
    CoachingResponse,
)


class CoachingRunPersistenceError(RuntimeError):
    pass


class SupabaseCoachingRunRepository:
    def __init__(
        self,
        settings: SupabaseSettings,
        http_client: httpx.Client | Any | None = None,
    ) -> None:
        if not settings.service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY가 필요합니다.")
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def save(
        self,
        user: AuthenticatedUser,
        request: CoachingAnalyzeRequest,
        response: CoachingResponse,
        context: CoachingContextBundle,
        model_name: str,
        *,
        prompt_version: str,
        skill_version: str,
    ) -> None:
        key = self.settings.service_role_key or ""
        try:
            result = self.http.post(
                f"{self.settings.url}/rest/v1/coaching_runs",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Prefer": "return=minimal",
                },
                json={
                    "user_id": user.user_id,
                    "answer_revision_id": str(request.answer_revision_id),
                    "job_snapshot_id": str(request.job_snapshot_id),
                    "status": response.status.value,
                    "response": response.model_dump(mode="json"),
                    "model_name": model_name,
                    "prompt_version": prompt_version,
                    "skill_version": skill_version,
                    "criteria_version": context.question.criteria_version,
                    "expires_at": context.practice_attempt.expires_at.isoformat(),
                },
            )
        except httpx.HTTPError as error:
            raise CoachingRunPersistenceError(
                "검증된 코칭 결과 저장소에 연결하지 못했습니다."
            ) from error
        if result.status_code not in (200, 201, 204):
            raise CoachingRunPersistenceError(
                "검증된 코칭 결과를 저장하지 못했습니다."
            )
