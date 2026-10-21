from typing import Literal

import re

from pydantic import Field, model_validator

from app.schemas.practice_setup import PracticeSetupModel

ResumeCategory = Literal["role", "career", "technology", "project", "education", "qualification"]


class ResumeFact(PracticeSetupModel):
    category: ResumeCategory
    value: str = Field(min_length=1, max_length=500)
    keyword: str | None = Field(default=None, min_length=1, max_length=80)
    page: int = Field(ge=1, le=10)
    source_excerpt: str = Field(min_length=2, max_length=300)


class ResumeAnalysisOutput(PracticeSetupModel):
    facts: list[ResumeFact] = Field(max_length=30)


class ResumeAnalysisResponse(ResumeAnalysisOutput):
    model: str


class ConfirmedResumeFact(PracticeSetupModel):
    category: ResumeCategory
    value: str = Field(min_length=1, max_length=500)
    keyword: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_recommendation_input(self):
        text = self.value + " " + (self.keyword or "")
        if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)0\d{1,2}[- .]?\d{3,4}[- .]?\d{4}(?!\d)|\d{6}\s*-\s*[1-4]\d{6}", text):
            raise ValueError("추천 정보에서 연락처·식별번호를 제거해 주세요.")
        if self.category == "technology" and not (self.keyword or "").strip():
            raise ValueError("추천에 사용할 기술명을 입력해 주세요.")
        if self.category != "technology" and self.keyword is not None:
            raise ValueError("기술 외 정보는 외부 검색어로 사용할 수 없습니다.")
        return self


class ConfirmedResumeProfile(PracticeSetupModel):
    facts: list[ConfirmedResumeFact] = Field(min_length=1, max_length=30)
