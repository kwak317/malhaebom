"""비교 후 면접 대화의 입력·모델 출력·API 계약."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID
import re
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)]
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=280)]
Point = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=280)]


class ChatContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InterviewChatRequest(ChatContract):
    action: Literal["start", "message", "finish"]
    request_id: UUID
    practice_session_id: UUID
    conversation_id: UUID | None = None
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)] | None = None

    @model_validator(mode="after")
    def check_action(self) -> Self:
        if self.action == "start":
            if self.conversation_id is not None or self.message is not None:
                raise ValueError("시작 요청에는 대화 ID와 메시지를 보내지 않습니다.")
        elif self.conversation_id is None:
            raise ValueError("후속 요청에는 대화 ID가 필요합니다.")
        if (self.action == "message") != (self.message is not None):
            raise ValueError("메시지는 message 요청에만 필요합니다.")
        return self


class InterviewSummary(ChatContract):
    clarified_points: Annotated[list[Point], Field(max_length=3)]
    next_practice: Annotated[list[Point], Field(min_length=1, max_length=2)]


class InterviewChatOutput(ChatContract):
    message: Text
    follow_up_question: Question | None
    memory: Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
    summary: InterviewSummary | None

    @field_validator("message")
    @classmethod
    def question_in_separate_field(cls, value: str) -> str:
        plain = re.sub(r"https?://[^\s<>]+", "", value)
        if "?" in plain or "？" in plain:
            raise ValueError("질문은 follow_up_question에만 작성합니다.")
        return value

    @field_validator("follow_up_question")
    @classmethod
    def single_question(cls, value: str | None) -> str | None:
        if value and value.count("?") + value.count("？") > 1:
            raise ValueError("꼬리질문은 한 번에 하나만 가능합니다.")
        return value


class InterviewChatResponse(ChatContract):
    conversation_id: UUID
    status: Literal["active", "finished"]
    message: Text
    follow_up_question: Question | None
    summary: InterviewSummary | None


class InterviewChatHistoryMessage(ChatContract):
    role: Literal["user", "assistant"]
    message: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    follow_up_question: Question | None = None
    summary: InterviewSummary | None = None

    @model_validator(mode="after")
    def check_role(self) -> Self:
        if self.role == "user" and (self.follow_up_question is not None or self.summary is not None):
            raise ValueError("사용자 메시지에는 코치 질문과 요약을 저장하지 않습니다.")
        return self


class InterviewChatHistory(ChatContract):
    conversation_id: UUID
    completed_at: datetime
    expires_at: datetime
    fingerprint: Annotated[list[str], Field(min_length=12, max_length=12)]
    messages: Annotated[list[InterviewChatHistoryMessage], Field(min_length=1)]

    @model_validator(mode="after")
    def check_finished(self) -> Self:
        if self.completed_at.tzinfo is None or self.expires_at.tzinfo is None or self.completed_at >= self.expires_at:
            raise ValueError("대화 기록은 원래 유효기간 안에서만 완료할 수 있습니다.")
        if self.messages[-1].role != "assistant" or self.messages[-1].summary is None:
            raise ValueError("완료된 대화 요약이 필요합니다.")
        return self
