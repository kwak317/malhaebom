from __future__ import annotations

from datetime import date

from pydantic import Field, field_validator

from app.schemas.alio_recruitment import AlioAnalyzedRequirement
from app.schemas.practice_setup import PracticeSetupModel


class MofeRecruitmentSummary(PracticeSetupModel):
    announcement_id: int
    company: str
    title: str
    source_url: str | None = None
    announced_at: date | None = None
    deadline: date | None = None
    location: str | None = None
    employment_type: str | None = None
    recruitment_type: str | None = None


class MofeRecruitmentSearchResponse(PracticeSetupModel):
    query: str
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=10)
    total_count: int = Field(ge=0)
    recruitments: list[MofeRecruitmentSummary]


class MofeRecruitmentAnalysisRequest(PracticeSetupModel):
    announcement_id: int = Field(gt=0)
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)

    @field_validator("company", "title")
    @classmethod
    def normalize_metadata(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("기관명과 공고 제목은 비어 있을 수 없습니다.")
        return normalized


class SaveAnalyzedMofeRecruitmentRequest(MofeRecruitmentAnalysisRequest):
    source_url: str = Field(min_length=1, max_length=1000)
    requirements: list[AlioAnalyzedRequirement] = Field(min_length=1, max_length=5)
