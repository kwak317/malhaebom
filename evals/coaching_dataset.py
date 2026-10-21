"""코칭 평가셋 계약과 규칙 기반 채점."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from evals.semantic_grader import SemanticAnnotation, evaluate_semantic

from app.schemas.coaching import (
    CoachingResponse,
    CriterionAssessmentLabel,
    IntentLabel,
    JobAlignmentLabel,
    ServerValidationContext,
)


class DatasetModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationQuestion(DatasetModel):
    question_id: str
    text: str


class EvidenceExpectation(DatasetModel):
    target_type: Literal["job_alignment", "criterion_assessment"]
    target_id: str
    segment_id: str
    quote: str
    support_segment_ids: list[str] = Field(default_factory=list)
    required: bool = True


class ExpectedJudgement(DatasetModel):
    status: Literal["ok", "needs_more_info"]
    intent_label: IntentLabel
    job_alignment: dict[str, JobAlignmentLabel]
    criterion_assessments: dict[str, CriterionAssessmentLabel]
    evidence: list[EvidenceExpectation] = Field(default_factory=list)
    failure_reason: str | None = None
    semantic: SemanticAnnotation | None = None
    critical_failure_conditions: list[str] = Field(default_factory=list)


class CoachingEvaluationCase(DatasetModel):
    dataset_version: Literal["v1", "v2"] = "v1"
    annotation_provenance: str | None = None
    exclude_job_alignment_and_status: bool = False
    id: str
    category: Literal["normal", "boundary", "failure"]
    question: EvaluationQuestion
    context: ServerValidationContext
    expected: ExpectedJudgement
    note: str
    why: str

    @model_validator(mode="after")
    def validate_case_consistency(self) -> Self:
        if self.category == "failure" and not self.expected.failure_reason:
            raise ValueError("실패 유도 사례에는 failure_reason이 필요합니다")
        if self.category != "failure" and self.expected.failure_reason is not None:
            raise ValueError("정상·경계 사례의 failure_reason은 null이어야 합니다")
        if set(self.expected.job_alignment) != set(self.context.requirement_ids):
            raise ValueError("기대 공고 판정 ID와 서버 requirement ID가 달라요")
        if set(self.expected.criterion_assessments) != set(
            self.context.active_criterion_ids
        ):
            raise ValueError("기대 기준 판정 ID와 서버 criterion ID가 달라요")
        if self.dataset_version == 'v2' and not self.exclude_job_alignment_and_status:
            raise ValueError('v2는 job alignment/status를 고정 점수에서 제외합니다')
        segments = {s.segment_id: s.text for s in self.context.answer_segments}
        for item in self.expected.evidence:
            if item.segment_id not in segments or not item.quote or item.quote not in segments[item.segment_id]:
                raise ValueError('expected quote는 해당 segment 원문이어야 합니다')
            if item.support_segment_ids and item.segment_id not in item.support_segment_ids:
                raise ValueError('expected quote segment는 support_segment_ids에 포함되어야 합니다')
            if not set(item.support_segment_ids) <= set(segments):
                raise ValueError('evidence support segment ID가 없습니다')
            allowed = (self.context.active_criterion_ids if item.target_type == 'criterion_assessment'
                       else self.context.requirement_ids)
            if item.target_id not in allowed:
                raise ValueError('evidence target ID가 없습니다')
            if self.dataset_version == 'v2' and not item.support_segment_ids:
                raise ValueError('v2 evidence에 support_segment_ids가 필요합니다')
        annotation = self.expected.semantic
        if annotation:
            segments = {s.segment_id for s in self.context.answer_segments}
            targets = set(self.context.active_criterion_ids)
            if not set(annotation.reason.support_segment_ids) <= segments:
                raise ValueError('annotation segment ID가 없습니다')
            if not set(annotation.action.acceptable_targets + annotation.clarifying_question.acceptable_targets) <= targets:
                raise ValueError('annotation target ID가 없습니다')
            if not set(annotation.action.priority_targets) <= set(annotation.action.acceptable_targets):
                raise ValueError('우선 대상은 허용 대상이어야 합니다')
        return self


class CaseScore(DatasetModel):
    contract_valid: bool
    judgement_correct: int = Field(ge=0)
    judgement_total: int = Field(ge=1)
    evidence_correct: int = Field(ge=0)
    evidence_total: int = Field(ge=0)
    label_results: dict[str, bool] = Field(default_factory=dict)
    semantic_evaluation: dict = Field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        evidence_weight = self.evidence_total
        total = self.judgement_total + evidence_weight
        correct = self.judgement_correct + self.evidence_correct
        return correct / total if self.contract_valid and total else 0.0


def load_dataset(path: Path) -> list[CoachingEvaluationCase]:
    cases: list[CoachingEvaluationCase] = []
    seen_ids: set[str] = set()
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue
        try:
            case = CoachingEvaluationCase.model_validate_json(raw_line)
        except Exception as error:
            raise ValueError(f"{path}:{line_number}: {error}") from error
        if case.id in seen_ids:
            raise ValueError(f"{path}:{line_number}: 중복 case id: {case.id}")
        seen_ids.add(case.id)
        cases.append(case)
    return cases


def score_response(
    case: CoachingEvaluationCase,
    response: CoachingResponse,
    semantic_review=None,
) -> CaseScore:
    expected = case.expected
    label_results = {"intent": response.intent_assessment.label == expected.intent_label}
    actual_jobs = {item.requirement_id: item.label for item in response.job_alignment}
    if not case.exclude_job_alignment_and_status:
        label_results["status"] = response.status.value == expected.status
        label_results.update({f"job:{item_id}": actual_jobs.get(item_id) == label
                              for item_id, label in expected.job_alignment.items()})
    correct = sum(label_results.values())
    total = len(label_results)

    actual_criteria = {
        item.criterion_id: item.assessment
        for item in response.criterion_assessments
    }
    for item_id, label in expected.criterion_assessments.items():
        label_results[f"criterion:{item_id}"] = actual_criteria.get(item_id) == label
        correct += int(actual_criteria.get(item_id) == label)
        total += 1

    actual_evidence = {
        (item.source_type, item.source_id, item.segment_id, item.quote)
        for item in response.evidence
    }
    expected_evidence = [item for item in expected.evidence
                         if not case.exclude_job_alignment_and_status or item.target_type != 'job_alignment']
    evidence_total = len(expected_evidence)
    if case.dataset_version == "v2":
        evidence_correct, evidence_total = _score_support_evidence(case, response, expected_evidence)
    else:
        evidence_correct = sum(
            (item.target_type, item.target_id, item.segment_id, item.quote) in actual_evidence
            for item in expected_evidence
        )
    return CaseScore(
        contract_valid=True,
        judgement_correct=correct,
        judgement_total=total,
        evidence_correct=evidence_correct,
        evidence_total=evidence_total,
        semantic_evaluation=evaluate_semantic(case, response.model_dump(mode="json"), semantic_review),
        label_results=label_results,
    )


def dataset_summary(cases: list[CoachingEvaluationCase]) -> dict[str, int]:
    return {
        category: sum(case.category == category for case in cases)
        for category in ("normal", "boundary", "failure")
    }


def _score_support_evidence(case, response, expectations):
    """지원 문장/원문 일치만 채점. 의미적 충분성은 사람 semantic 검토에 남긴다."""
    supports = {}
    required = set()
    for item in expectations:
        supports.setdefault(item.target_id, set()).update(item.support_segment_ids)
        if item.required:
            required.add(item.target_id)
    segments = {s.segment_id: s.text for s in case.context.answer_segments}
    correct = total = 0
    for assessment in response.criterion_assessments:
        relevant = []
        for evidence in assessment.evidence:
            supported = (evidence.segment_id in supports.get(assessment.criterion_id, set())
                         and bool(evidence.quote)
                         and evidence.quote in segments.get(evidence.segment_id, ""))
            relevant.append(supported)
        # 기준별 한 항목: 필요한 인용이 있고 반환한 모든 인용이 지원 문장에 맞아야 통과.
        # 선택 근거 누락은 벌점 처리하지 않는다. 좋은 인용에 잘못된 인용을 섞어도 실패.
        if assessment.criterion_id in required or relevant:
            total += 1
            correct += int(bool(relevant) and all(relevant))
    return correct, total
