from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

from pydantic import Field, field_validator

from app.schemas.practice_setup import PracticeSetupModel


class AlioRecruitmentSummary(PracticeSetupModel):
    announcement_id: int
    company: str
    title: str
    source_url: str | None = None
    announced_at: date | None = None
    deadline: date | None = None
    location: str | None = None
    employment_type: str | None = None
    recruitment_type: str | None = None


class AlioRecruitmentSearchResponse(PracticeSetupModel):
    query: str
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=10)
    total_count: int = Field(ge=0)
    recruitments: list[AlioRecruitmentSummary]


class AlioAnalyzedRequirement(PracticeSetupModel):
    text: str = Field(min_length=2, max_length=300)
    source_excerpt: str = Field(min_length=2, max_length=500)

    @field_validator("text", "source_excerpt")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("요구사항과 원문 근거 문구는 2자 이상이어야 합니다.")
        return normalized


class AlioRecruitmentAnalysisRequest(PracticeSetupModel):
    announcement_id: int = Field(gt=0)
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    source_url: str = Field(min_length=1, max_length=1000)

    @field_validator("company", "title")
    @classmethod
    def normalize_metadata(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("기관명과 공고 제목은 비어 있을 수 없습니다.")
        return normalized

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlparse(normalized)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("AI 분석에는 ALIO 검색 결과의 HTTPS 원문 URL만 사용할 수 있습니다.")
        return normalized


class SaveAnalyzedAlioRecruitmentRequest(AlioRecruitmentAnalysisRequest):
    requirements: list[AlioAnalyzedRequirement] = Field(min_length=1, max_length=5)
