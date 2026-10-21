from __future__ import annotations

from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from app.core.auth import AuthenticatedUser
from app.core.supabase_settings import SupabaseSettings
from app.schemas.coaching import AnswerSegment
from app.services.supabase_persistence import SupabasePersistenceError


class SupabaseAnswerRevisionRepository:
    def __init__(
        self,
        settings: SupabaseSettings,
        http_client: httpx.Client | Any | None = None,
    ) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def create_revision(
        self,
        user: AuthenticatedUser,
        *,
        analysis_job_id: UUID,
        confirmed_text: str,
        answer_segments: list[AnswerSegment],
    ) -> dict[str, object]:
        response = self._request(
            "POST",
            "/rest/v1/rpc/create_answer_revision",
            user,
            json={
                "p_analysis_job_id": str(analysis_job_id),
                "p_confirmed_text": confirmed_text,
                "p_answer_segments": [
                    segment.model_dump(mode="json") for segment in answer_segments
                ],
            },
        )
        try:
            revision_id = response.json()
        except ValueError as error:
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "답변 revision 응답을 처리하지 못했습니다."
            ) from error
        if not isinstance(revision_id, str):
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "답변 revision을 만들지 못했습니다."
            )
        result = self._request(
            "GET",
            "/rest/v1/answer_revisions"
            f"?id=eq.{quote(revision_id, safe='')}&select=*",
            user,
        )
        rows = _json_list(result)
        if not rows:
            raise KeyError(revision_id)
        return rows[0]

    def get_job_snapshot_id(
        self, user: AuthenticatedUser, practice_session_id: UUID
    ) -> UUID | None:
        response = self._request(
            "GET",
            "/rest/v1/practice_sessions"
            f"?id=eq.{quote(str(practice_session_id), safe='')}"
            "&select=job_posting_id",
            user,
        )
        rows = _json_list(response)
        if not rows or not isinstance(rows[0].get("job_posting_id"), str):
            return None
        return UUID(str(rows[0]["job_posting_id"]))

    def _request(
        self,
        method: str,
        path: str,
        user: AuthenticatedUser,
        **kwargs: Any,
    ) -> Any:
        headers = {
            "apikey": self.settings.publishable_key,
            "Authorization": f"Bearer {user.access_token}",
        }
        try:
            response = self.http.request(
                method,
                f"{self.settings.url}{path}",
                headers=headers,
                **kwargs,
            )
        except httpx.HTTPError as error:
            raise SupabasePersistenceError(
                "PERSISTENCE_UNAVAILABLE", "답변 저장소에 연결하지 못했습니다."
            ) from error
        if response.status_code not in (200, 201):
            code = (
                "INVALID_ANSWER_REVISION"
                if response.status_code in (400, 409, 422)
                else "PERSISTENCE_FAILED"
            )
            message = (
                "완료되고 만료되지 않은 본인 분석 결과만 확정할 수 있습니다."
                if code == "INVALID_ANSWER_REVISION"
                else "답변 revision 저장 요청에 실패했습니다."
            )
            raise SupabasePersistenceError(code, message)
        return response


def _json_list(response: Any) -> list[dict[str, object]]:
    try:
        value = response.json()
    except ValueError as error:
        raise SupabasePersistenceError(
            "PERSISTENCE_FAILED", "답변 저장소 응답을 처리하지 못했습니다."
        ) from error
    return value if isinstance(value, list) else []
