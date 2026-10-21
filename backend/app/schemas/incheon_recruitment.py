from __future__ import annotations

from datetime import date

from pydantic import Field

from app.schemas.practice_setup import PracticeSetupModel


class IncheonRecruitmentSummary(PracticeSetupModel):
    announcement_id: int
    company: str
    title: str
    source_url: str
    announced_at: date | None = None
    deadline: date | None = None
    location: str | None = None
    employment_type: str | None = None
    recruitment_type: str | None = None


class IncheonRecruitmentSearchResponse(PracticeSetupModel):
    query: str
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=10)
    total_count: int = Field(ge=0)
    recruitments: list[IncheonRecruitmentSummary]
