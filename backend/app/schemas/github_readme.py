from __future__ import annotations

from pydantic import Field

from app.schemas.practice_setup import PracticeSetupModel


class GithubReadmeAnalysisRequest(PracticeSetupModel):
    source_url: str = Field(min_length=1, max_length=1000)


class ReadmeTechnology(PracticeSetupModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=2, max_length=220)
    source_excerpt: str = Field(min_length=2, max_length=240)


class ReadmeFlowStep(PracticeSetupModel):
    description: str = Field(min_length=2, max_length=260)
    source_excerpt: str = Field(min_length=2, max_length=240)


class GithubReadmeAnalysisOutput(PracticeSetupModel):
    technology_stack: list[ReadmeTechnology] = Field(min_length=1, max_length=8)
    project_flow: list[ReadmeFlowStep] = Field(min_length=1, max_length=6)


class GithubReadmeAnalysisResponse(GithubReadmeAnalysisOutput):
    source_url: str
    readme_sha: str
    model: str
