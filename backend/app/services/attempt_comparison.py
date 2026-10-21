"""저장된 1·2차 코칭 결과를 추가 LLM 호출 없이 비교한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from app.core.auth import AuthenticatedUser
from app.services.practice_history import (
    coaching_content_analysis_from_response,
    compare_attempts,
)


DEMO_PREVIOUS_COACHING_RUN_ID = UUID("a0000000-0000-4000-8000-000000000001")
DEMO_CURRENT_COACHING_RUN_ID = UUID("a0000000-0000-4000-8000-000000000002")
DEMO_COMPARISON_SESSION_ID = UUID("90000000-0000-4000-8000-000000000001")
DEMO_COMPARISON_JOB_ID = UUID("80000000-0000-4000-8000-000000000001")


class AttemptComparisonNotFound(KeyError):
    """요청한 코칭 결과가 없거나 소유·만료 경계 밖인 경우."""


class AttemptComparisonConflict(ValueError):
    """두 코칭 결과를 같은 조건으로 비교할 수 없는 경우."""


class AttemptComparisonRepository(Protocol):
    def get_coaching_runs(
        self,
        *,
        user_id: str,
        previous_coaching_run_id: UUID,
        current_coaching_run_id: UUID,
    ) -> list[dict[str, object]]: ...


class AttemptComparisonService:
    def __init__(self, repository: AttemptComparisonRepository | Any) -> None:
        self.repository = repository

    def compare(
        self,
        user: AuthenticatedUser,
        *,
        previous_coaching_run_id: UUID,
        current_coaching_run_id: UUID,
        now: datetime | None = None,
    ) -> dict[str, object]:
        if previous_coaching_run_id == current_coaching_run_id:
            raise AttemptComparisonConflict(
                "서로 다른 1차·2차 코칭 결과가 필요합니다."
            )

        rows = self.repository.get_coaching_runs(
            user_id=user.user_id,
            previous_coaching_run_id=previous_coaching_run_id,
            current_coaching_run_id=current_coaching_run_id,
        )
        rows_by_id = {
            str(row.get("id")): row
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("id"), str)
        }
        try:
            previous = _validated_run(
                rows_by_id[str(previous_coaching_run_id)], user, now
            )
            current = _validated_run(
                rows_by_id[str(current_coaching_run_id)], user, now
            )
        except KeyError as error:
            raise AttemptComparisonNotFound() from error

        _require_compatible(previous, current)
        if previous["attempt_no"] != 1 or current["attempt_no"] != 2:
            raise AttemptComparisonConflict(
                "1차 코칭 결과와 2차 코칭 결과 순서로만 비교할 수 있습니다."
            )

        comparison = compare_attempts(
            _comparison_attempt(previous),
            _comparison_attempt(current),
        )
        return {
            "previous_coaching_run_id": str(previous_coaching_run_id),
            "current_coaching_run_id": str(current_coaching_run_id),
            "practice_session_id": previous["practice_session_id"],
            "question_id": previous["question_id"],
            "job_snapshot_id": previous["job_snapshot_id"],
            "model_name": previous["model_name"],
            "prompt_version": previous["prompt_version"],
            "skill_version": previous["skill_version"],
            "comparison": comparison,
        }


def _validated_run(
    row: dict[str, object],
    user: AuthenticatedUser,
    now: datetime | None,
) -> dict[str, object]:
    active_now = now or datetime.now(UTC)
    revision = row.get("answer_revisions")
    if not isinstance(revision, dict):
        raise AttemptComparisonNotFound()
    analysis_job = revision.get("analysis_jobs")
    if not isinstance(analysis_job, dict):
        raise AttemptComparisonNotFound()

    run_user_id = _text(row.get("user_id"))
    revision_user_id = _text(revision.get("user_id"))
    if run_user_id != user.user_id or revision_user_id != user.user_id:
        raise AttemptComparisonNotFound()
    if (
        _datetime(row.get("expires_at")) <= active_now
        or _datetime(revision.get("expires_at")) <= active_now
        or _datetime(analysis_job.get("expires_at")) <= active_now
    ):
        raise AttemptComparisonNotFound()
    if analysis_job.get("status") != "completed":
        raise AttemptComparisonNotFound()

    response = row.get("response")
    if not isinstance(response, dict):
        raise AttemptComparisonNotFound()
    if row.get("status") not in {"ok", "needs_more_info"} or response.get(
        "status"
    ) not in {"ok", "needs_more_info"}:
        raise AttemptComparisonConflict(
            "완료된 구조화 코칭 결과만 비교할 수 있습니다."
        )

    normalized = {
        "id": _required_text(row.get("id")),
        "user_id": run_user_id,
        "job_snapshot_id": _required_text(row.get("job_snapshot_id")),
        "model_name": _required_text(row.get("model_name")),
        "prompt_version": _required_text(row.get("prompt_version")),
        "skill_version": _required_text(row.get("skill_version")),
        "created_at": _datetime(row.get("created_at")).isoformat(),
        "response": response,
        "practice_session_id": _required_text(revision.get("practice_session_id")),
        "question_id": _required_text(revision.get("question_id")),
        "confirmed_text": _required_text(revision.get("confirmed_text")),
        "delivery_metrics": (
            revision.get("delivery_metrics")
            if isinstance(revision.get("delivery_metrics"), dict)
            else {}
        ),
        "attempt_no": _attempt_no(analysis_job.get("attempt_no")),
    }
    return normalized


def _require_compatible(
    previous: dict[str, object], current: dict[str, object]
) -> None:
    fields = (
        "practice_session_id",
        "question_id",
        "job_snapshot_id",
        "model_name",
        "prompt_version",
        "skill_version",
    )
    mismatched = [field for field in fields if previous[field] != current[field]]
    if mismatched:
        raise AttemptComparisonConflict(
            "두 코칭 결과의 비교 조건이 다릅니다: " + ", ".join(mismatched)
        )


def _comparison_attempt(run: dict[str, object]) -> dict[str, object]:
    transcript = _required_text(run.get("confirmed_text"))
    content_analysis = coaching_content_analysis_from_response(
        run.get("response"), transcript
    )
    attempt: dict[str, object] = {
        "attempt_no": run["attempt_no"],
        "metrics": run["delivery_metrics"],
    }
    if content_analysis is not None:
        attempt["content_analysis"] = content_analysis
    return attempt


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _required_text(value: object) -> str:
    text = _text(value).strip()
    if not text:
        raise AttemptComparisonNotFound()
    return text


def _datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise AttemptComparisonNotFound() from error
    else:
        raise AttemptComparisonNotFound()
    if parsed.tzinfo is None:
        raise AttemptComparisonNotFound()
    return parsed.astimezone(UTC)


def _attempt_no(value: object) -> int:
    if value in {1, 2} and not isinstance(value, bool):
        return int(value)
    raise AttemptComparisonNotFound()


class InMemoryAttemptComparisonRepository:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def get_coaching_runs(
        self,
        *,
        user_id: str,
        previous_coaching_run_id: UUID,
        current_coaching_run_id: UUID,
    ) -> list[dict[str, object]]:
        allowed = {str(previous_coaching_run_id), str(current_coaching_run_id)}
        return [
            row
            for row in self.rows
            if row.get("id") in allowed and row.get("user_id") == user_id
        ]


def build_demo_attempt_comparison_service(
    user_id: str,
    *,
    now: datetime | None = None,
) -> AttemptComparisonService:
    active_now = now or datetime.now(UTC)
    expires_at = (active_now + timedelta(hours=24)).isoformat()

    def row(
        run_id: UUID,
        attempt_no: int,
        transcript: str,
        assessment: str,
        evidence: list[dict[str, str]],
        needed: str | None,
        cpm: int,
    ) -> dict[str, object]:
        return {
            "id": str(run_id),
            "user_id": user_id,
            "job_snapshot_id": str(DEMO_COMPARISON_JOB_ID),
            "status": "ok",
            "response": {
                "status": "ok",
                "criterion_assessments": [
                    {
                        "criterion_id": "result_verification",
                        "assessment": assessment,
                        "reason": "결과 확인 설명을 비교합니다.",
                        "evidence": evidence,
                        "needed": needed,
                    }
                ],
            },
            "model_name": "mock-v1",
            "prompt_version": "coaching-output-v3",
            "skill_version": "interview-coach-v4",
            "created_at": active_now.isoformat(),
            "expires_at": expires_at,
            "answer_revisions": {
                "id": f"70000000-0000-4000-8000-00000000000{attempt_no}",
                "user_id": user_id,
                "practice_session_id": str(DEMO_COMPARISON_SESSION_ID),
                "question_id": "preset-04",
                "confirmed_text": transcript,
                "delivery_metrics": {
                    "cpm": cpm,
                    "long_silence_count": 3 - attempt_no,
                    "repetition_count": 2 - attempt_no,
                },
                "expires_at": expires_at,
                "analysis_jobs": {
                    "attempt_no": attempt_no,
                    "status": "completed",
                    "expires_at": expires_at,
                },
            },
        }

    return AttemptComparisonService(
        InMemoryAttemptComparisonRepository(
            [
                row(
                    DEMO_PREVIOUS_COACHING_RUN_ID,
                    1,
                    "수정후 결과를 확인하지 못했습니다.",
                    "not_observed",
                    [],
                    "수정 후 확인 방법과 결과",
                    330,
                ),
                row(
                    DEMO_CURRENT_COACHING_RUN_ID,
                    2,
                    "수정 후 공백과 일반 입력에서 로그인 성공을 확인했습니다.",
                    "met",
                    [
                        {
                            "segment_id": "demo-rev2-s1",
                            "quote": "공백과 일반 입력에서 로그인 성공을 확인했습니다.",
                        }
                    ],
                    None,
                    300,
                ),
            ]
        )
    )
