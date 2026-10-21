from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class QuestionTtsRequest(BaseModel):
    question: str


class CoachTtsRequest(BaseModel):
    text: str


class QuestionTtsResponse(BaseModel):
    audioUrl: str
    text: str
    durationMs: int
    expiresAt: datetime
