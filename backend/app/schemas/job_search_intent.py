from __future__ import annotations

from pydantic import Field, model_validator

from app.schemas.practice_setup import PracticeSetupModel


class JobSearchIntentRequest(PracticeSetupModel):
    message: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def normalize_message(self) -> "JobSearchIntentRequest":
        self.message = " ".join(self.message.split())
        if not self.message:
            raise ValueError("메시지를 입력해 주세요.")
        return self


class JobSearchIntentResponse(PracticeSetupModel):
    should_search: bool
    query: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_query(self) -> "JobSearchIntentResponse":
        self.query = " ".join(self.query.split()) if self.query else None
        if self.should_search and not self.query:
            raise ValueError("공고 검색 의도에는 검색어가 필요합니다.")
        if not self.should_search:
            self.query = None
        return self
