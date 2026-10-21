from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from app.schemas.interview_chat import InterviewChatHistory

from app.core.auth import AuthenticatedUser
from app.services.supabase_persistence import SupabaseAnalysisRepository
from app.services.coaching_skill import load_skill_bundle


CRITERION_DESCRIPTIONS = {
    "problem_context": "문제 상황",
    "cause_observation": "원인 관찰 신호",
    "cause_inference": "원인 추론 연결",
    "own_action": "본인의 해결 행동",
    "action_rationale": "행동 선택 이유",
    "result_verification": "결과 확인",
}
for criterion in load_skill_bundle().catalog.criteria:
    CRITERION_DESCRIPTIONS.setdefault(criterion.id, criterion.name)


class PracticeHistoryService:
    def __init__(self, repository: SupabaseAnalysisRepository | Any) -> None:
        self.repository = repository

    def list_records(self, user: AuthenticatedUser) -> dict[str, object]:
        return {"records": _records_from_rows(self.repository.list_completed_jobs(user))}

    def get_record(self, user: AuthenticatedUser, practice_session_id: str) -> dict[str, object]:
        rows = self.repository.get_completed_session_jobs(user, practice_session_id)
        records = _records_from_rows(rows)
        if not records:
            raise KeyError(practice_session_id)
        return records[0]

    def delete_record(self, user: AuthenticatedUser, practice_session_id: str) -> None:
        self.repository.get_completed_session_jobs(user, practice_session_id)
        rows = self.repository.get_session_jobs(user, practice_session_id)
        self.repository.delete_session_jobs(user, practice_session_id, rows)

    def delete_all_records(self, user: AuthenticatedUser) -> None:
        session_ids = [record["practice_session_id"] for record in _records_from_rows(self.repository.list_completed_jobs(user))]
        for practice_session_id in session_ids:
            self.delete_record(user, str(practice_session_id))

def _records_from_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    sessions: OrderedDict[str, list[dict[str, object]]] = OrderedDict()
    for row in rows:
        practice_session_id = _string(row.get("practice_session_id"))
        if not practice_session_id:
            continue
        sessions.setdefault(practice_session_id, []).append(row)

    records: list[dict[str, object]] = []
    for practice_session_id, session_rows in sessions.items():
        ordered_rows = sorted(session_rows, key=lambda row: _number(row.get("attempt_no")))
        first = ordered_rows[0]
        completed_at = max((_string(row.get("completed_at")) for row in ordered_rows), default="")
        attempts = [_attempt_from_row(row) for row in ordered_rows]
        record: dict[str, object] = {
            "practice_session_id": practice_session_id,
            "question_type": _string(first.get("question_type")),
            "question_id": _nullable_string(first.get("question_id")),
            "custom_question_text": _nullable_string(first.get("custom_question_text")),
            "practiced_at": completed_at,
            "attempts": attempts,
        }
        first_attempt = next(
            (attempt for attempt in attempts if attempt["attempt_no"] == 1), None
        )
        second_attempt = next(
            (attempt for attempt in attempts if attempt["attempt_no"] == 2), None
        )
        if first_attempt is not None and second_attempt is not None:
            record["comparison"] = compare_attempts(first_attempt, second_attempt)
            history = _interview_chat_history(ordered_rows)
            if history is not None:
                record["interview_chat"] = history
        records.append(record)
        if len(records) == 50:
            break
    return records


def _interview_chat_history(rows: list[dict[str, object]]) -> dict[str, object] | None:
    second = next((row for row in rows if row.get("attempt_no") == 2), None)
    result = second.get("result") if second else None
    if not isinstance(result, dict) or not result.get("interview_chat"):
        return None
    try:
        history = InterviewChatHistory.model_validate(result["interview_chat"])
    except ValidationError:
        return None
    if history.expires_at <= datetime.now(UTC):
        return None
    fingerprint = []
    for row in rows:
        revision = _latest_revision(row.get("answer_revisions"))
        runs = [item for item in _list(revision.get("coaching_runs")) if isinstance(item, dict)] if revision else []
        if not runs:
            return None
        run = max(runs, key=lambda item: _string(item.get("created_at")))
        version = [_string(run.get(name)) for name in ("model_name", "prompt_version", "skill_version", "criteria_version")]
        if not all(version):
            return None
        fingerprint.extend([_string(revision.get("id")), _string(run.get("created_at")), *version])
    if fingerprint != history.fingerprint:
        return None
    return history.model_dump(mode="json", exclude={"fingerprint", "expires_at"})


def _attempt_from_row(row: dict[str, object]) -> dict[str, object]:
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    delivery = row.get("delivery") if isinstance(row.get("delivery"), dict) else {}
    metrics = delivery.get("metrics") if isinstance(delivery.get("metrics"), dict) else {}
    feedback = delivery.get("feedback") if isinstance(delivery.get("feedback"), list) else []
    revision = _latest_revision(row.get("answer_revisions"))
    confirmed_text = _string(revision.get("confirmed_text")) if revision else ""
    revision_metrics = (
        revision.get("delivery_metrics")
        if revision and isinstance(revision.get("delivery_metrics"), dict)
        else {}
    )
    attempt: dict[str, object] = {
        "attempt_no": _number(row.get("attempt_no")),
        "job_id": _string(row.get("id")),
        "transcript": confirmed_text or _string(result.get("text")),
        "metrics": {
            "cpm": _number_or_none(revision_metrics.get("cpm"))
            if revision_metrics
            else _number_or_none(metrics.get("cpm")),
            "long_silence_count": _number(revision_metrics.get("long_silence_count"))
            if revision_metrics
            else len(_list(metrics.get("long_silences"))),
            "repetition_count": _number(revision_metrics.get("repetition_count"))
            if revision_metrics
            else len(_list(metrics.get("repetitions"))),
        },
        "feedback": [
            action
            for item in feedback
            if isinstance(item, dict)
            for action in [_string(item.get("action"))]
            if action
        ][:2],
    }
    content_analysis = _coaching_content_analysis(
        revision, _string(attempt["transcript"])
    ) or _content_analysis(result.get("content_feedback"))
    if content_analysis is not None:
        attempt["content_analysis"] = content_analysis
    return attempt


def _latest_revision(value: object) -> dict[str, object] | None:
    revisions = [item for item in _list(value) if isinstance(item, dict)]
    if not revisions:
        return None
    return max(revisions, key=lambda item: _string(item.get("confirmed_at")))


def _coaching_content_analysis(
    revision: dict[str, object] | None, transcript: str
) -> dict[str, object] | None:
    if revision is None:
        return None
    runs = [
        item
        for item in _list(revision.get("coaching_runs"))
        if isinstance(item, dict)
    ]
    if not runs:
        return None
    latest = max(runs, key=lambda item: _string(item.get("created_at")))
    response = latest.get("response")
    return coaching_content_analysis_from_response(response, transcript)


def coaching_content_analysis_from_response(
    response: object, transcript: str
) -> dict[str, object] | None:
    """저장 완료된 코칭 응답을 비교 전용 기준 분석으로 축소한다."""

    if not isinstance(response, dict) or response.get("status") not in {
        "ok",
        "needs_more_info",
    }:
        return None

    criteria: list[dict[str, object]] = []
    for item in _list(response.get("criterion_assessments")):
        if not isinstance(item, dict):
            return None
        criterion_id = _string(item.get("criterion_id"))
        assessment = _string(item.get("assessment"))
        reason = _string(item.get("reason"))
        if (
            not criterion_id
            or assessment not in {"met", "partial", "not_observed", "undetermined"}
            or not reason
        ):
            return None
        evidence = [
            quote
            for evidence_item in _list(item.get("evidence"))
            if isinstance(evidence_item, dict)
            for quote in [_string(evidence_item.get("quote"))]
            if quote and quote in transcript
        ]
        criteria.append({
            "criterion_id": criterion_id,
            "description": CRITERION_DESCRIPTIONS.get(criterion_id, criterion_id),
            "assessment": assessment,
            "reason": reason,
            "evidence": evidence,
            "needed": _nullable_string(item.get("needed")),
        })
    if not criteria or len({item["criterion_id"] for item in criteria}) != len(criteria):
        return None
    return {"criteria": criteria}


def _content_analysis(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    rubric = value.get("rubric")
    raw_concepts = rubric.get("required_concepts") if isinstance(rubric, dict) else None
    if not isinstance(raw_concepts, list):
        return None

    concepts: list[dict[str, str]] = []
    for item in raw_concepts:
        if not isinstance(item, dict):
            return None
        criterion_id = _string(item.get("id"))
        description = _string(item.get("description"))
        if not criterion_id or not description:
            return None
        concepts.append({"criterion_id": criterion_id, "description": description})
    if not concepts or len({item["criterion_id"] for item in concepts}) != len(concepts):
        return None

    covered: dict[str, str] = {}
    for item in _list(value.get("covered_concepts")):
        if not isinstance(item, dict):
            continue
        criterion_id = _string(item.get("id"))
        evidence = _string(item.get("evidence"))
        if criterion_id and evidence:
            covered[criterion_id] = evidence

    contradictions: dict[str, dict[str, object]] = {}
    for item in _list(value.get("contradictions")):
        if not isinstance(item, dict):
            continue
        criterion_id = _string(item.get("id"))
        reason = _string(item.get("reason"))
        evidence = [quote for quote in _list(item.get("evidence")) if isinstance(quote, str) and quote]
        if criterion_id and reason and len(evidence) == 2:
            contradictions[criterion_id] = {"reason": reason, "evidence": evidence}

    criteria: list[dict[str, object]] = []
    for concept in concepts:
        criterion_id = concept["criterion_id"]
        contradiction = contradictions.get(criterion_id)
        if contradiction is not None:
            criteria.append({
                **concept,
                "assessment": "undetermined",
                "reason": contradiction["reason"],
                "evidence": contradiction["evidence"],
                "needed": "상충하는 설명을 실제 기록에 맞게 정리해 주세요.",
            })
        elif criterion_id in covered:
            criteria.append({
                **concept,
                "assessment": "met",
                "reason": "답변에서 설명이 확인됐습니다.",
                "evidence": [covered[criterion_id]],
                "needed": None,
            })
        else:
            criteria.append({
                **concept,
                "assessment": "not_observed",
                "reason": "답변에서 확인되지 않았습니다.",
                "evidence": [],
                "needed": concept["description"],
            })

    return {"criteria": criteria}


def compare_attempts(
    first: dict[str, object], second: dict[str, object]
) -> dict[str, object]:
    """저장된 두 시도의 기준 판정과 전달력 수치를 서버 규칙으로 비교한다."""

    comparison: dict[str, object] = {
        "content_available": False,
        "content_notice": "두 답변의 구조화 내용 분석이 모두 있어야 기준별로 비교할 수 있어요.",
        "criteria": [],
        "added_explanations": [],
        "still_missing": [],
        "contradictions": [],
        "delivery": _compare_delivery(first, second),
    }
    first_content = first.get("content_analysis")
    second_content = second.get("content_analysis")
    if not isinstance(first_content, dict) or not isinstance(second_content, dict):
        return comparison
    first_criteria = _criteria_by_id(first_content.get("criteria"))
    second_criteria = _criteria_by_id(second_content.get("criteria"))
    if not first_criteria or set(first_criteria) != set(second_criteria):
        comparison["content_notice"] = (
            "두 답변에 적용된 기준이 달라 내용 상태를 직접 비교하지 않았어요."
        )
        return comparison

    criteria: list[dict[str, object]] = []
    added: list[dict[str, object]] = []
    still_missing: list[dict[str, object]] = []
    contradictions: list[dict[str, object]] = []
    for criterion_id, first_item in first_criteria.items():
        second_item = second_criteria[criterion_id]
        description = _string(second_item.get("description")) or _string(
            first_item.get("description")
        )
        first_assessment = _string(first_item.get("assessment"))
        second_assessment = _string(second_item.get("assessment"))
        criterion = {
            "criterion_id": criterion_id,
            "description": description,
            "first": _public_assessment(first_item),
            "second": _public_assessment(second_item),
            "change": _assessment_change(first_assessment, second_assessment),
        }
        criteria.append(criterion)
        if (
            first_assessment in {"not_observed", "undetermined"}
            and second_assessment == "met"
        ):
            added.append({
                "criterion_id": criterion_id,
                "description": description,
                "evidence": _string_list(second_item.get("evidence")),
            })
        if second_assessment != "met":
            still_missing.append({
                "criterion_id": criterion_id,
                "description": description,
                "assessment": second_assessment,
                "needed": _nullable_string(second_item.get("needed")),
            })
        for attempt_no, item in ((1, first_item), (2, second_item)):
            evidence = _string_list(item.get("evidence"))
            if _string(item.get("assessment")) == "undetermined" and len(evidence) >= 2:
                contradictions.append({
                    "attempt_no": attempt_no,
                    "criterion_id": criterion_id,
                    "description": description,
                    "reason": _string(item.get("reason")),
                    "evidence": evidence,
                })

    comparison.update({
        "content_available": True,
        "content_notice": None,
        "criteria": criteria,
        "added_explanations": added,
        "still_missing": still_missing,
        "contradictions": contradictions,
    })
    return comparison


def _criteria_by_id(value: object) -> dict[str, dict[str, object]]:
    criteria: dict[str, dict[str, object]] = {}
    for item in _list(value):
        if not isinstance(item, dict):
            return {}
        criterion_id = _string(item.get("criterion_id"))
        if not criterion_id or criterion_id in criteria:
            return {}
        criteria[criterion_id] = item
    return criteria


def _public_assessment(item: dict[str, object]) -> dict[str, object]:
    return {
        "assessment": _string(item.get("assessment")),
        "reason": _string(item.get("reason")),
        "evidence": _string_list(item.get("evidence")),
        "needed": _nullable_string(item.get("needed")),
    }


def _assessment_change(first: str, second: str) -> str:
    if first == second:
        return "unchanged"
    if first in {"not_observed", "undetermined"} and second == "met":
        return "added"
    if first == "met" and second != "met":
        return "no_longer_observed"
    return "changed"


def _compare_delivery(
    first: dict[str, object], second: dict[str, object]
) -> dict[str, object]:
    first_metrics = first.get("metrics") if isinstance(first.get("metrics"), dict) else {}
    second_metrics = second.get("metrics") if isinstance(second.get("metrics"), dict) else {}
    return {
        "cpm": _metric_change(first_metrics.get("cpm"), second_metrics.get("cpm")),
        "long_silence_count": _metric_change(
            first_metrics.get("long_silence_count"),
            second_metrics.get("long_silence_count"),
        ),
        "repetition_count": _metric_change(
            first_metrics.get("repetition_count"),
            second_metrics.get("repetition_count"),
        ),
    }


def _metric_change(first: object, second: object) -> dict[str, object]:
    before = _number_or_none(first)
    after = _number_or_none(second)
    if before is None or after is None:
        direction = "unavailable"
    elif after > before:
        direction = "increased"
    elif after < before:
        direction = "decreased"
    else:
        direction = "same"
    return {"first": before, "second": after, "direction": direction}


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _nullable_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _number(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _number_or_none(value: object) -> int | float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [item for item in _list(value) if isinstance(item, str) and item]
