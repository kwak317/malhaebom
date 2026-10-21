from __future__ import annotations

import re
from typing import Protocol
from uuid import UUID, uuid4

from app.core.auth import AuthenticatedUser
from app.schemas.answer_revision import (
    AnswerRevisionCreateRequest,
    AnswerRevisionResponse,
)
from app.schemas.coaching import AnswerSegment


class AnswerRevisionRepository(Protocol):
    def create_revision(
        self,
        user: AuthenticatedUser,
        *,
        analysis_job_id: UUID,
        confirmed_text: str,
        answer_segments: list[AnswerSegment],
    ) -> dict[str, object]: ...

    def get_job_snapshot_id(
        self, user: AuthenticatedUser, practice_session_id: UUID
    ) -> UUID | None: ...


class AnswerRevisionService:
    def __init__(self, repository: AnswerRevisionRepository) -> None:
        self.repository = repository

    def confirm(
        self,
        user: AuthenticatedUser,
        analysis_job_id: UUID,
        request: AnswerRevisionCreateRequest,
    ) -> AnswerRevisionResponse:
        normalized_text = normalize_confirmed_text(request.confirmed_text)
        segments = split_answer_segments(normalized_text)
        row = self.repository.create_revision(
            user,
            analysis_job_id=analysis_job_id,
            confirmed_text=normalized_text,
            answer_segments=segments,
        )
        practice_session_id = UUID(str(row["practice_session_id"]))
        return AnswerRevisionResponse(
            answer_revision_id=UUID(str(row["id"])),
            analysis_job_id=UUID(str(row["analysis_job_id"])),
            practice_session_id=practice_session_id,
            question_id=str(row["question_id"]),
            answer_segments=row["answer_segments"],
            confirmed_at=row["confirmed_at"],
            expires_at=row["expires_at"],
            job_snapshot_id=self.repository.get_job_snapshot_id(
                user, practice_session_id
            ),
        )


def normalize_confirmed_text(value: str) -> str:
    normalized_lines = [
        re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()
    ]
    normalized = "\n".join(line for line in normalized_lines if line).strip()
    if not 1 <= len(normalized) <= 5000:
        raise ValueError("확정할 전사문은 1~5000자여야 합니다.")
    return normalized


def split_answer_segments(value: str) -> list[AnswerSegment]:
    sentences = [
        match.group(0).strip()
        for match in re.finditer(r".+?(?:[.!?。！？]+(?=\s|$)|$)", value, re.DOTALL)
        if match.group(0).strip()
    ]
    if not sentences:
        sentences = [value]
    return [
        AnswerSegment(segment_id=f"segment-{uuid4()}", text=sentence)
        for sentence in sentences
    ]
