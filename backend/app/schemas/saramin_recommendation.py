from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.alio_recruitment import AlioAnalyzedRequirement
from app.schemas.github_readme import GithubReadmeAnalysisResponse
from app.schemas.practice_setup import PracticeSetupModel
from app.schemas.resume import ConfirmedResumeProfile


class SaraminRecommendationRequest(PracticeSetupModel):
    selected_ncs_ids: list[str] = Field(min_length=1, max_length=9)
    readme_analysis: GithubReadmeAnalysisResponse | None = None
    resume_profile: ConfirmedResumeProfile | None = None
    preparation_conversation_id: UUID | None = None


class SaraminRecommendation(PracticeSetupModel):
    company: str
    title: str
    source_url: str
    deadline: date | None
    experience: str
    matched_technologies: list[str]
    matched_project_flows: list[str]
    matched_ncs_labels: list[str]
    source_excerpt: str
    matched_resume_technologies: list[str] = Field(default_factory=list)
    matched_resume_project_flows: list[str] = Field(default_factory=list)
    matched_chat_experience: list[str] = Field(default_factory=list)


class SaraminRecommendationResponse(PracticeSetupModel):
    recommendations: list[SaraminRecommendation]
    searched_at: str


class ReviewRecommendedJobRequest(PracticeSetupModel):
    source_url: str = Field(min_length=1, max_length=1000)


class SaveReviewedPrivateJobRequest(PracticeSetupModel):
    source: Literal["saramin", "jobkorea", "rallit", "wanted", "jumpit"]
    posting_id: str = Field(pattern=r"^[0-9]{1,12}$")
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    source_url: str = Field(min_length=1, max_length=1000)
    requirements: list[AlioAnalyzedRequirement] = Field(min_length=1, max_length=5)
