"""LLM 호출과 코칭 출력 검증을 이 파일 하나로 모읍니다.

라우터나 UI 코드가 openai를 직접 import하지 않게 하세요.
3차에서 이 파일 내부만 갈아끼우면 나머지는 그대로 돌아갑니다.

현재 책임지는 것:
  - 출력 계약 검증 (Pydantic)
  - 서버가 허용한 ID와 답변 원문 인용 검증
  - 검증된 응답의 evidence·gaps·status 계산

실제 provider 재시도·폴백과 Langfuse 전송은 모델 선정 뒤 이 경계 안에 연결합니다.
"""

import re
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from app.schemas.coaching import (
    CoachingLLMOutput,
    CoachingResponse,
    CoachingStatus,
    ConsolidatedEvidence,
    CriterionAssessmentLabel,
    Gap,
    IntentAssessment,
    IntentLabel,
    JobAlignmentLabel,
    ServerValidationContext,
    TargetType,
    TerminalResponseReason,
)


class OutputContractError(ValueError):
    """형식 또는 서버 참조 검증에 실패한 미노출 LLM 결과."""

    def __init__(self, violations: Iterable[str]) -> None:
        self.violations = tuple(violations)
        super().__init__("; ".join(self.violations))


KOREAN_TEXT_PATTERN = re.compile(r"[가-힣]")
PLACEHOLDER_ACTIONS = {"-", "n/a", "na", "none", "null", "없음", "해당 없음"}


def validate_and_build_response(
    raw_output: dict[str, Any] | CoachingLLMOutput,
    context: ServerValidationContext,
) -> CoachingResponse:
    """형식과 서버 참조를 모두 검증한 뒤 계산 필드를 포함해 반환한다."""

    try:
        llm_output = (
            raw_output
            if isinstance(raw_output, CoachingLLMOutput)
            else CoachingLLMOutput.model_validate(raw_output)
        )
    except ValidationError as exc:
        raise OutputContractError(_format_pydantic_errors(exc)) from exc

    violations: list[str] = []
    _check_exact_ids(
        name="requirement_id",
        returned=[item.requirement_id for item in llm_output.job_alignment],
        expected=context.requirement_ids,
        violations=violations,
    )
    _check_exact_ids(
        name="criterion_id",
        returned=[item.criterion_id for item in llm_output.criterion_assessments],
        expected=context.active_criterion_ids,
        violations=violations,
    )

    segment_texts = {
        segment.segment_id: segment.text for segment in context.answer_segments
    }
    for owner, evidence_items in _iter_evidence(llm_output):
        seen_quotes: set[tuple[str, str]] = set()
        for evidence in evidence_items:
            key = (evidence.segment_id, evidence.quote)
            if key in seen_quotes:
                violations.append(f"{owner}: 같은 evidence가 중복됐습니다")
                continue
            seen_quotes.add(key)

            segment_text = segment_texts.get(evidence.segment_id)
            if segment_text is None:
                violations.append(
                    f"{owner}: 허용되지 않은 segment_id '{evidence.segment_id}'입니다"
                )
            elif evidence.quote not in segment_text:
                violations.append(
                    f"{owner}: quote가 문장 '{evidence.segment_id}'에 정확히 존재하지 않습니다"
                )

    allowed_criterion_ids = set(context.active_criterion_ids)
    allowed_metric_ids = set(context.allowed_delivery_metric_ids)
    for index, action in enumerate(llm_output.next_actions):
        if (
            action.target_type is TargetType.CRITERION
            and action.target_id not in allowed_criterion_ids
        ):
            violations.append(
                f"next_actions[{index}]: 허용되지 않은 criterion target_id "
                f"'{action.target_id}'입니다"
            )
        if (
            action.target_type is TargetType.DELIVERY_METRIC
            and action.target_id not in allowed_metric_ids
        ):
            violations.append(
                f"next_actions[{index}]: 허용되지 않은 delivery_metric target_id "
                f"'{action.target_id}'입니다"
            )

    answer_numbers = _numeric_tokens(" ".join(segment_texts.values()))
    invented_numbers = sorted(
        _numeric_tokens(llm_output.example_answer) - answer_numbers
    )
    if invented_numbers:
        violations.append(
            "example_answer: 확정 답변에 없는 숫자 "
            + ", ".join(invented_numbers)
            + "를 사용할 수 없습니다"
        )

    _validate_user_facing_korean(llm_output, violations)

    all_criteria_met = all(
        item.assessment is CriterionAssessmentLabel.MET
        for item in llm_output.criterion_assessments
    )
    if all_criteria_met and llm_output.clarifying_question is not None:
        violations.append(
            "모든 활성 기준이 met이면 clarifying_question은 null이어야 합니다"
        )

    if violations:
        raise OutputContractError(violations)

    gaps = [
        Gap(
            criterion_id=item.criterion_id,
            assessment=item.assessment.value,
            reason=item.reason,
            needed=item.needed,
        )
        for item in llm_output.criterion_assessments
        if item.assessment is not CriterionAssessmentLabel.MET
    ]
    evidence = _consolidate_evidence(llm_output)

    needs_more_info = (
        bool(gaps)
        or llm_output.intent_assessment.label is not IntentLabel.ALIGNED
        or any(
            item.label is not JobAlignmentLabel.RELATED
            for item in llm_output.job_alignment
        )
    )

    return CoachingResponse(
        status=(
            CoachingStatus.NEEDS_MORE_INFO
            if needs_more_info
            else CoachingStatus.OK
        ),
        job_alignment=llm_output.job_alignment,
        intent_assessment=llm_output.intent_assessment,
        criterion_assessments=llm_output.criterion_assessments,
        evidence=evidence,
        gaps=gaps,
        clarifying_question=llm_output.clarifying_question,
        next_actions=llm_output.next_actions,
        example_answer=llm_output.example_answer,
    )


def build_terminal_response(reason: TerminalResponseReason) -> CoachingResponse:
    """지원 범위 밖 요청이나 시스템 실패를 LLM 없이 서버에서 만든다."""

    return CoachingResponse(
        status=reason.status,
        intent_assessment=IntentAssessment(
            label=IntentLabel.UNDETERMINED,
            reason=reason.reason,
        ),
    )


def _check_exact_ids(
    *, name: str, returned: list[str], expected: list[str], violations: list[str]
) -> None:
    duplicates = sorted({item for item in returned if returned.count(item) > 1})
    missing = sorted(set(expected) - set(returned))
    unexpected = sorted(set(returned) - set(expected))

    if duplicates:
        violations.append(f"{name} 중복: {', '.join(duplicates)}")
    if missing:
        violations.append(f"{name} 누락: {', '.join(missing)}")
    if unexpected:
        violations.append(f"허용되지 않은 {name}: {', '.join(unexpected)}")


def _iter_evidence(llm_output: CoachingLLMOutput):
    for item in llm_output.job_alignment:
        yield f"job_alignment[{item.requirement_id}]", item.evidence
    for item in llm_output.criterion_assessments:
        yield f"criterion_assessments[{item.criterion_id}]", item.evidence


def _validate_user_facing_korean(
    llm_output: CoachingLLMOutput, violations: list[str]
) -> None:
    texts: list[tuple[str, str | None]] = [
        ("intent_assessment.reason", llm_output.intent_assessment.reason),
        ("clarifying_question", llm_output.clarifying_question),
        ("example_answer", llm_output.example_answer),
    ]
    texts.extend(
        (f"job_alignment[{item.requirement_id}].reason", item.reason)
        for item in llm_output.job_alignment
    )
    for item in llm_output.criterion_assessments:
        texts.append(
            (f"criterion_assessments[{item.criterion_id}].reason", item.reason)
        )
        texts.append(
            (f"criterion_assessments[{item.criterion_id}].needed", item.needed)
        )
    texts.extend(
        (f"next_actions[{index}].action", item.action)
        for index, item in enumerate(llm_output.next_actions)
    )

    for name, value in texts:
        if value is not None and not KOREAN_TEXT_PATTERN.search(value):
            violations.append(f"{name}: 사용자 노출 문장은 한국어여야 합니다")

    for index, item in enumerate(llm_output.next_actions):
        if item.action.strip().casefold() in PLACEHOLDER_ACTIONS:
            violations.append(
                f"next_actions[{index}].action: 구체적인 연습 행동이 필요합니다"
            )


def _consolidate_evidence(
    llm_output: CoachingLLMOutput,
) -> list[ConsolidatedEvidence]:
    consolidated: list[ConsolidatedEvidence] = []
    for item in llm_output.job_alignment:
        consolidated.extend(
            ConsolidatedEvidence(
                source_type="job_alignment",
                source_id=item.requirement_id,
                segment_id=evidence.segment_id,
                quote=evidence.quote,
                reason=item.reason,
            )
            for evidence in item.evidence
        )
    for item in llm_output.criterion_assessments:
        consolidated.extend(
            ConsolidatedEvidence(
                source_type="criterion_assessment",
                source_id=item.criterion_id,
                segment_id=evidence.segment_id,
                quote=evidence.quote,
                reason=item.reason,
            )
            for evidence in item.evidence
        )
    return consolidated


def _format_pydantic_errors(exc: ValidationError) -> list[str]:
    formatted = []
    for error in exc.errors(include_url=False):
        location = ".".join(str(part) for part in error["loc"])
        formatted.append(f"{location}: {error['msg']}")
    return formatted


def _numeric_tokens(value: str) -> set[str]:
    """대필 위험이 큰 신규 수치가 예시 답변에 추가되는 것을 차단한다."""

    return set(re.findall(r"\d+(?:[.,]\d+)*", value))
