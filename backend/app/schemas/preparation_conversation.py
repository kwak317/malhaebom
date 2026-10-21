"""준비 대화 후보의 모델 출력. 실행 결과가 아닌 요청 계약이다."""
from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SmallText = Annotated[str, StringConstraints(min_length=1, max_length=300)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ExperienceFact(Contract):
    kind: Literal["company", "period", "role", "responsibility", "project", "action", "outcome", "technology"]
    value: SmallText
    source_message_id: SmallText
    source_excerpt: SmallText


class ProfileUpdate(Contract):
    action: Literal["propose", "request_save", "discard"]
    draft_id: SmallText | None
    draft_version: Annotated[int, Field(ge=1)] | None
    review_stage: Literal["collecting", "awaiting_confirmation"] | None
    facts: Annotated[list[ExperienceFact], Field(max_length=12)]


class PreparationConversationOutput(Contract):
    intent: Literal["answer", "clarify", "correction", "profile_update", "change_step", "out_of_scope", "refusal", "support"]
    message: Annotated[str, StringConstraints(min_length=1, max_length=800)]
    follow_up_question: Annotated[str, StringConstraints(min_length=1, max_length=280)] | None
    next_action: Literal["stay", "request_change_stage", "request_skip", "request_rerecord"]
    requested_stage: Literal["ncs", "readme", "resume", "interview"] | None
    profile_update: ProfileUpdate | None
