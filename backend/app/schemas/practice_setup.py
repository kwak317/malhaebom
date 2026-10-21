from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.applicant_context import ApplicantContext


class PracticeSetupModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobRequirementSummary(PracticeSetupModel):
    id: UUID
    code: str
    text: str
    display_order: int
    source_excerpt: str | None = None


class JobPostingSummary(PracticeSetupModel):
    id: UUID
    company: str
    title: str
    source_url: str
    captured_at: datetime
    data_origin: Literal["reviewed", "demo", "alio", "public_job", "mofe_job", "private_job"]
    requirements: list[JobRequirementSummary]


class JobPostingListResponse(PracticeSetupModel):
    job_postings: list[JobPostingSummary]


class CreatePracticeSessionRequest(PracticeSetupModel):
    applicant_context: ApplicantContext | None = None
    job_posting_id: UUID
    requirement_ids: list[UUID] = Field(min_length=1, max_length=2)
    question_type: Literal["preset", "custom"]
    question_id: str | None = Field(default=None, pattern=r"^preset-[0-9]{2}$")
    custom_question_text: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_question_and_requirements(self) -> "CreatePracticeSessionRequest":
        if len(set(self.requirement_ids)) != len(self.requirement_ids):
            raise ValueError("요구사항은 중복해서 선택할 수 없습니다.")

        custom_text = (
            self.custom_question_text.strip()
            if self.custom_question_text is not None
            else None
        )
        if self.question_type == "preset":
            if self.question_id is None or custom_text:
                raise ValueError("기본 질문에는 question_id만 필요합니다.")
            self.custom_question_text = None
            return self

        if self.question_id is not None or not custom_text:
            raise ValueError("직접 입력 질문은 1~200자여야 합니다.")
        self.custom_question_text = custom_text
        return self


class PracticeSessionResponse(PracticeSetupModel):
    practice_session_id: UUID
    expires_at: datetime
