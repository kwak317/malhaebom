from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.core.auth import AuthenticatedUser
from app.schemas.alio_recruitment import SaveAnalyzedAlioRecruitmentRequest
from app.schemas.public_employment_recruitment import (
    SaveAnalyzedPublicEmploymentRecruitmentRequest,
)
from app.schemas.mofe_recruitment import SaveAnalyzedMofeRecruitmentRequest
from app.schemas.saramin_recommendation import SaveReviewedPrivateJobRequest
from app.schemas.practice_setup import (
    CreatePracticeSessionRequest,
    JobPostingListResponse,
    JobPostingSummary,
    JobRequirementSummary,
    PracticeSessionResponse,
)


class PracticeSetupUnavailable(RuntimeError):
    pass


class PracticeSetupRepository(Protocol):
    def list_job_postings(self, user: AuthenticatedUser) -> list[dict[str, object]]: ...

    def create_practice_session(
        self, user: AuthenticatedUser, request: CreatePracticeSessionRequest
    ) -> str: ...

    def save_analyzed_alio_recruitment(
        self, user: AuthenticatedUser, request: SaveAnalyzedAlioRecruitmentRequest
    ) -> str: ...

    def save_analyzed_public_employment_recruitment(
        self,
        user: AuthenticatedUser,
        request: SaveAnalyzedPublicEmploymentRecruitmentRequest,
    ) -> str: ...

    def save_analyzed_mofe_recruitment(
        self, user: AuthenticatedUser, request: SaveAnalyzedMofeRecruitmentRequest
    ) -> str: ...

    def save_reviewed_private_job(
        self, user: AuthenticatedUser, request: SaveReviewedPrivateJobRequest
    ) -> str: ...

    def get_practice_session(
        self, user: AuthenticatedUser, practice_session_id: str
    ) -> dict[str, object]: ...


class PracticeSetupService:
    def __init__(self, repository: PracticeSetupRepository) -> None:
        self.repository = repository

    def list_job_postings(
        self, user: AuthenticatedUser
    ) -> JobPostingListResponse:
        return JobPostingListResponse(
            job_postings=self._job_posting_summaries(
                self.repository.list_job_postings(user)
            )
        )

    def save_analyzed_alio_recruitment(
        self,
        user: AuthenticatedUser,
        request: SaveAnalyzedAlioRecruitmentRequest,
    ) -> JobPostingSummary:
        created_job_id = self.repository.save_analyzed_alio_recruitment(user, request)
        for posting in self._job_posting_summaries(self.repository.list_job_postings(user)):
            if str(posting.id) == created_job_id:
                return posting
        raise PracticeSetupUnavailable("검토 완료 공고를 확인하지 못했습니다.")

    def save_analyzed_public_employment_recruitment(
        self,
        user: AuthenticatedUser,
        request: SaveAnalyzedPublicEmploymentRecruitmentRequest,
    ) -> JobPostingSummary:
        created_job_id = self.repository.save_analyzed_public_employment_recruitment(
            user, request
        )
        for posting in self._job_posting_summaries(self.repository.list_job_postings(user)):
            if str(posting.id) == created_job_id:
                return posting
        raise PracticeSetupUnavailable("검토 완료 공고를 확인하지 못했습니다.")

    def save_analyzed_mofe_recruitment(
        self,
        user: AuthenticatedUser,
        request: SaveAnalyzedMofeRecruitmentRequest,
    ) -> JobPostingSummary:
        created_job_id = self.repository.save_analyzed_mofe_recruitment(user, request)
        for posting in self._job_posting_summaries(self.repository.list_job_postings(user)):
            if str(posting.id) == created_job_id:
                return posting
        raise PracticeSetupUnavailable("검토 완료 공고를 확인하지 못했습니다.")

    def save_reviewed_private_job(
        self,
        user: AuthenticatedUser,
        request: SaveReviewedPrivateJobRequest,
    ) -> JobPostingSummary:
        created_job_id = self.repository.save_reviewed_private_job(user, request)
        for posting in self._job_posting_summaries(self.repository.list_job_postings(user)):
            if str(posting.id) == created_job_id:
                return posting
        raise PracticeSetupUnavailable("검토 완료 공고를 확인하지 못했습니다.")

    @staticmethod
    def _job_posting_summaries(
        rows: list[dict[str, object]],
    ) -> list[JobPostingSummary]:
        postings: list[JobPostingSummary] = []
        for row in rows:
            raw_requirements = row.get("job_requirements")
            if not isinstance(raw_requirements, list):
                raw_requirements = []
            requirements = sorted(
                (
                    JobRequirementSummary(
                        id=requirement["id"],
                        code=str(requirement["code"]),
                        text=str(requirement["requirement_text"]),
                        display_order=int(requirement["display_order"]),
                        source_excerpt=(
                            str(requirement["source_excerpt"])
                            if isinstance(requirement.get("source_excerpt"), str)
                            else None
                        ),
                    )
                    for requirement in raw_requirements
                    if isinstance(requirement, dict)
                ),
                key=lambda item: item.display_order,
            )
            if not requirements:
                continue
            postings.append(
                JobPostingSummary(
                    id=row["id"],
                    company=str(row["company"]),
                    title=str(row["title"]),
                    source_url=str(row["source_url"]),
                    captured_at=row["captured_at"],
                    data_origin=row["data_origin"],
                    requirements=requirements,
                )
            )
        return postings

    def create_practice_session(
        self,
        user: AuthenticatedUser,
        request: CreatePracticeSessionRequest,
    ) -> PracticeSessionResponse:
        session_id = self.repository.create_practice_session(user, request)
        row = self.repository.get_practice_session(user, session_id)
        expires_at = row.get("expires_at")
        if not isinstance(expires_at, str):
            raise PracticeSetupUnavailable("연습 세션 만료 시각을 확인하지 못했습니다.")
        return PracticeSessionResponse(
            practice_session_id=UUID(session_id),
            expires_at=datetime.fromisoformat(expires_at.replace("Z", "+00:00")).astimezone(UTC),
        )


class UnavailablePracticeSetupService:
    def list_job_postings(self, user: AuthenticatedUser) -> JobPostingListResponse:
        raise PracticeSetupUnavailable("공고 저장소가 설정되지 않았습니다.")

    def create_practice_session(
        self,
        user: AuthenticatedUser,
        request: CreatePracticeSessionRequest,
    ) -> PracticeSessionResponse:
        raise PracticeSetupUnavailable("공고 저장소가 설정되지 않았습니다.")

    def save_analyzed_alio_recruitment(
        self,
        user: AuthenticatedUser,
        request: SaveAnalyzedAlioRecruitmentRequest,
    ) -> JobPostingSummary:
        raise PracticeSetupUnavailable("공고 저장소가 설정되지 않았습니다.")

    def save_analyzed_public_employment_recruitment(
        self,
        user: AuthenticatedUser,
        request: SaveAnalyzedPublicEmploymentRecruitmentRequest,
    ) -> JobPostingSummary:
        raise PracticeSetupUnavailable("공고 저장소가 설정되지 않았습니다.")

    def save_analyzed_mofe_recruitment(
        self, user: AuthenticatedUser, request: SaveAnalyzedMofeRecruitmentRequest
    ) -> JobPostingSummary:
        raise PracticeSetupUnavailable("공고 저장소가 설정되지 않았습니다.")

    def save_reviewed_private_job(
        self, user: AuthenticatedUser, request: SaveReviewedPrivateJobRequest
    ) -> JobPostingSummary:
        raise PracticeSetupUnavailable("공고 저장소가 설정되지 않았습니다.")
