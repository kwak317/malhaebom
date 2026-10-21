from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx
import os
from app.services.preparation_conversation_repository import confirmed_context, supplemental_context_path

from app.core.supabase_settings import SupabaseSettings
from app.schemas.coaching import (
    JobContext,
    JobRequirementContext,
    PracticeAttemptContext,
    QuestionContext,
)
from app.services.coaching_context import CoachingContextService
from app.services.coaching_questions import get_preset_coaching_question, get_custom_coaching_question


class CoachingContextPersistenceError(RuntimeError):
    pass


class SupabaseCoachingContextRepository:
    """MCP 프로세스 안에서만 service-role로 읽는 코칭 문맥 저장소."""

    def __init__(
        self,
        settings: SupabaseSettings,
        http_client: httpx.Client | Any | None = None,
    ) -> None:
        if not settings.service_role_key:
            raise CoachingContextPersistenceError(
                "SUPABASE_SERVICE_ROLE_KEY가 필요합니다."
            )
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def get_question(self, question_id: str) -> QuestionContext | None:
        return get_preset_coaching_question(question_id)

    def get_custom_question(self, attempt: PracticeAttemptContext) -> QuestionContext | None:
        session_id = quote(str(attempt.practice_session_id), safe="")
        user_id = quote(attempt.user_id, safe="")
        now = datetime.now(UTC)
        rows = self._get(
            "/rest/v1/practice_sessions"
            f"?id=eq.{session_id}&user_id=eq.{user_id}&question_type=eq.custom"
            f"&expires_at=gt.{quote(now.isoformat(), safe='')}"
            "&select=id,user_id,question_type,custom_question_text,expires_at"
        )
        if not rows:
            return None
        row = rows[0]
        # Service-role reads still require the owned revision's exact session.
        if (str(row.get("id")) != str(attempt.practice_session_id)
                or str(row.get("user_id")) != attempt.user_id
                or row.get("question_type") != "custom"
                or datetime.fromisoformat(str(row.get("expires_at")).replace("Z", "+00:00")) <= now):
            return None
        return get_custom_coaching_question(attempt.question_id, row.get("custom_question_text"))

    def get_practice_attempt(
        self, answer_revision_id: UUID
    ) -> PracticeAttemptContext | None:
        revision_id = quote(str(answer_revision_id), safe="")
        now = quote(datetime.now(UTC).isoformat(), safe="")
        rows = self._get(
            "/rest/v1/answer_revisions"
            f"?id=eq.{revision_id}&expires_at=gt.{now}"
            "&select=id,user_id,practice_session_id,question_id,answer_segments,"
            "delivery_metrics,confirmed_at,expires_at"
        )
        if not rows:
            return None
        row = rows[0]
        return PracticeAttemptContext(
            answer_revision_id=row["id"],
            user_id=str(row["user_id"]),
            practice_session_id=row["practice_session_id"],
            question_id=str(row["question_id"]),
            answer_segments=row["answer_segments"],
            delivery_metrics=_scalar_delivery_metrics(row.get("delivery_metrics")),
            confirmed_at=row["confirmed_at"],
            expires_at=row["expires_at"],
        )

    def get_job_context(
        self, job_snapshot_id: UUID, practice_session_id: UUID
    ) -> JobContext | None:
        job_id = quote(str(job_snapshot_id), safe="")
        session_id = quote(str(practice_session_id), safe="")
        sessions = self._get(
            "/rest/v1/practice_sessions"
            f"?id=eq.{session_id}&job_posting_id=eq.{job_id}"
            "&select=id,user_id,job_posting_id,expires_at,applicant_context"
        )
        if not sessions:
            return None
        session = sessions[0]
        postings = self._get(
            "/rest/v1/job_postings"
            f"?id=eq.{job_id}"
            "&select=id,source_url,captured_at,review_status"
        )
        if not postings:
            return None
        selected = self._get(
            "/rest/v1/practice_session_requirements"
            f"?practice_session_id=eq.{session_id}"
            "&select=requirement_id,job_requirements(code,requirement_text)"
        )
        requirements: list[JobRequirementContext] = []
        for item in selected:
            requirement = item.get("job_requirements")
            if not isinstance(requirement, dict):
                continue
            requirements.append(
                JobRequirementContext(
                    requirement_id=str(requirement.get("code") or item["requirement_id"]),
                    text=str(requirement["requirement_text"]),
                    category="required",
                )
            )
        if not requirements:
            return None
        posting = postings[0]
        return JobContext(
            job_snapshot_id=job_snapshot_id,
            user_id=str(session["user_id"]),
            practice_session_id=practice_session_id,
            source_url=str(posting["source_url"]),
            captured_at=posting["captured_at"],
            review_status=posting["review_status"],
            requirements=requirements,
            expires_at=session["expires_at"],
            applicant_context=session.get("applicant_context"),
            supplemental_context=(confirmed_context(self._get(supplemental_context_path(practice_session_id, session["user_id"])))
                if os.getenv("PREPARATION_CONVERSATION_ENABLED") == "true" else []),
        )

    def _get(self, path: str) -> list[dict[str, object]]:
        key = self.settings.service_role_key or ""
        try:
            response = self.http.get(
                f"{self.settings.url}{path}",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
        except httpx.HTTPError as error:
            raise CoachingContextPersistenceError(
                "코칭 문맥 저장소에 연결하지 못했습니다."
            ) from error
        if response.status_code != 200:
            raise CoachingContextPersistenceError(
                f"코칭 문맥 저장소 요청에 실패했습니다. (HTTP {response.status_code})"
            )
        try:
            value = response.json()
        except ValueError as error:
            raise CoachingContextPersistenceError(
                "코칭 문맥 저장소 응답을 처리하지 못했습니다."
            ) from error
        return value if isinstance(value, list) else []


def _scalar_delivery_metrics(value: object) -> dict[str, float | int | None]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): metric
        for key, metric in value.items()
        if metric is None or isinstance(metric, (int, float)) and not isinstance(metric, bool)
    }


def build_supabase_coaching_context_service() -> CoachingContextService:
    settings = SupabaseSettings.from_env(require_service_role=True)
    return CoachingContextService(SupabaseCoachingContextRepository(settings))
