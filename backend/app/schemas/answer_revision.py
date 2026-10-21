from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.coaching import AnswerSegment


class AnswerRevisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AnswerRevisionCreateRequest(AnswerRevisionModel):
    confirmed_text: str = Field(min_length=1, max_length=5000)


class AnswerRevisionResponse(AnswerRevisionModel):
    answer_revision_id: UUID
    analysis_job_id: UUID
    practice_session_id: UUID
    question_id: str
    answer_segments: list[AnswerSegment]
    confirmed_at: datetime
    expires_at: datetime
    job_snapshot_id: UUID | None
