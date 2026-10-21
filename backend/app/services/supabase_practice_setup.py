from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.core.auth import AuthenticatedUser
from app.core.supabase_settings import SupabaseSettings
from app.schemas.alio_recruitment import SaveAnalyzedAlioRecruitmentRequest
from app.schemas.public_employment_recruitment import (
    SaveAnalyzedPublicEmploymentRecruitmentRequest,
)
from app.schemas.mofe_recruitment import SaveAnalyzedMofeRecruitmentRequest
from app.schemas.saramin_recommendation import SaveReviewedPrivateJobRequest
from app.schemas.practice_setup import CreatePracticeSessionRequest
from app.services.supabase_persistence import SupabasePersistenceError


class SupabasePracticeSetupRepository:
    """사용자 JWT를 유지하는 공고 조회·연습 세션 생성 adapter."""

    def __init__(
        self,
        settings: SupabaseSettings,
        http_client: httpx.Client | Any | None = None,
    ) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def list_job_postings(
        self, user: AuthenticatedUser
    ) -> list[dict[str, object]]:
        select = quote(
            "id,company,title,source_url,captured_at,data_origin,"
            "job_requirements(id,code,requirement_text,source_excerpt,display_order)",
            safe=",()",
        )
        response = self._request(
            "GET",
            "/rest/v1/job_postings"
            f"?review_status=eq.reviewed&is_active=eq.true&select={select}"
            "&order=company.asc,title.asc",
            user,
        )
        return _json_list(response)

    def save_analyzed_alio_recruitment(
        self, user: AuthenticatedUser, request: SaveAnalyzedAlioRecruitmentRequest
    ) -> str:
        response = self._request(
            "POST",
            "/rest/v1/rpc/review_alio_recruitment",
            user,
            json={
                "p_announcement_id": request.announcement_id,
                "p_company": request.company,
                "p_title": request.title,
                "p_source_url": request.source_url,
                "p_requirements": [
                    {
                        "text": requirement.text,
                        "source_excerpt": requirement.source_excerpt,
                    }
                    for requirement in request.requirements
                ],
            },
        )
        try:
            value = response.json()
        except ValueError as error:
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고 응답을 처리하지 못했습니다."
            ) from error
        if not isinstance(value, str):
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고를 저장하지 못했습니다."
            )
        return value

    def save_analyzed_public_employment_recruitment(
        self,
        user: AuthenticatedUser,
        request: SaveAnalyzedPublicEmploymentRecruitmentRequest,
    ) -> str:
        response = self._request(
            "POST",
            "/rest/v1/rpc/review_public_employment_recruitment",
            user,
            json={
                "p_announcement_id": request.announcement_id,
                "p_company": request.company,
                "p_title": request.title,
                "p_source_url": request.source_url,
                "p_requirements": [
                    {
                        "text": requirement.text,
                        "source_excerpt": requirement.source_excerpt,
                    }
                    for requirement in request.requirements
                ],
            },
        )
        try:
            value = response.json()
        except ValueError as error:
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고 응답을 처리하지 못했습니다."
            ) from error
        if not isinstance(value, str):
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고를 저장하지 못했습니다."
            )
        return value

    def save_analyzed_mofe_recruitment(
        self,
        user: AuthenticatedUser,
        request: SaveAnalyzedMofeRecruitmentRequest,
    ) -> str:
        response = self._request(
            "POST",
            "/rest/v1/rpc/review_mofe_recruitment",
            user,
            json={
                "p_announcement_id": request.announcement_id,
                "p_company": request.company,
                "p_title": request.title,
                "p_source_url": request.source_url,
                "p_requirements": [
                    {
                        "text": requirement.text,
                        "source_excerpt": requirement.source_excerpt,
                    }
                    for requirement in request.requirements
                ],
            },
        )
        try:
            value = response.json()
        except ValueError as error:
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고 응답을 처리하지 못했습니다."
            ) from error
        if not isinstance(value, str):
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고를 저장하지 못했습니다."
            )
        return value

    def save_reviewed_private_job(
        self, user: AuthenticatedUser, request: SaveReviewedPrivateJobRequest
    ) -> str:
        key = self.settings.service_role_key
        if not key:
            raise SupabasePersistenceError(
                "CONFIGURATION_ERROR", "민간 공고 검토 저장소가 설정되지 않았습니다."
            )
        try:
            response = self.http.request(
                "POST",
                f"{self.settings.url}/rest/v1/rpc/review_private_job_recruitment",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                json={
                    "p_reviewer_id": user.user_id,
                    "p_source": request.source,
                    "p_posting_id": request.posting_id,
                    "p_company": request.company,
                    "p_title": request.title,
                    "p_source_url": request.source_url,
                    "p_requirements": [requirement.model_dump() for requirement in request.requirements],
                },
            )
        except httpx.HTTPError as error:
            raise SupabasePersistenceError(
                "PERSISTENCE_UNAVAILABLE", "공고 저장소에 연결하지 못했습니다."
            ) from error
        if response.status_code not in (200, 201):
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고를 저장하지 못했습니다."
            )
        try:
            value = response.json()
        except ValueError as error:
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고 응답을 처리하지 못했습니다."
            ) from error
        if not isinstance(value, str):
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "검토 공고를 저장하지 못했습니다."
            )
        return value

    def create_practice_session(
        self, user: AuthenticatedUser, request: CreatePracticeSessionRequest
    ) -> str:
        response = self._request(
            "POST",
            ("/rest/v1/rpc/create_practice_session_with_applicant_context"
             if request.applicant_context is not None else "/rest/v1/rpc/create_practice_session"),
            user,
            json={
                "p_job_posting_id": str(request.job_posting_id),
                "p_requirement_ids": [str(value) for value in request.requirement_ids],
                "p_question_type": request.question_type,
                "p_question_id": request.question_id,
                "p_custom_question_text": request.custom_question_text,
                **({"p_applicant_context": request.applicant_context.model_dump(mode="json")}
                   if request.applicant_context is not None else {}),
            },
        )
        try:
            value = response.json()
        except ValueError as error:
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "연습 세션 응답을 처리하지 못했습니다."
            ) from error
        if not isinstance(value, str):
            raise SupabasePersistenceError(
                "PERSISTENCE_FAILED", "연습 세션을 만들지 못했습니다."
            )
        return value

    def get_practice_session(
        self, user: AuthenticatedUser, practice_session_id: str
    ) -> dict[str, object]:
        session_id = quote(practice_session_id, safe="")
        response = self._request(
            "GET",
            "/rest/v1/practice_sessions"
            f"?id=eq.{session_id}&select=id,user_id,job_posting_id,"
            "question_type,question_id,custom_question_text,expires_at",
            user,
        )
        rows = _json_list(response)
        if not rows:
            raise KeyError(practice_session_id)
        return rows[0]

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
                "PERSISTENCE_UNAVAILABLE", "공고 저장소에 연결하지 못했습니다."
            ) from error
        if response.status_code not in (200, 201):
            if response.status_code == 404:
                code = "NOT_FOUND"
                message = "선택한 공고 또는 요구사항을 찾지 못했습니다."
            elif response.status_code in (400, 409, 422):
                code = "INVALID_PRACTICE_SETUP"
                message = "공고·요구사항·질문 선택을 확인해 주세요."
            else:
                code = "PERSISTENCE_FAILED"
                message = "공고 저장소 요청에 실패했습니다."
            raise SupabasePersistenceError(code, message)
        return response


def _json_list(response: Any) -> list[dict[str, object]]:
    try:
        value = response.json()
    except ValueError as error:
        raise SupabasePersistenceError(
            "PERSISTENCE_FAILED", "공고 저장소 응답을 처리하지 못했습니다."
        ) from error
    return value if isinstance(value, list) else []
