"""말해봄 코칭 요청·서버 문맥·출력 계약."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.applicant_context import ApplicantContext


NonEmptyText = Annotated[str, Field(min_length=1)]
ExampleAnswerText = Annotated[str, Field(min_length=1, max_length=500)]
QuestionId = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$"),
]


class ContractModel(BaseModel):
    """알 수 없는 필드와 공백뿐인 문자열을 허용하지 않는 기본 모델."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CoachingStatus(StrEnum):
    OK = "ok"
    NEEDS_MORE_INFO = "needs_more_info"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"


class JobAlignmentLabel(StrEnum):
    RELATED = "related"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNCLEAR = "unclear"


class IntentLabel(StrEnum):
    ALIGNED = "aligned"
    PARTIAL = "partial"
    OFF_TOPIC = "off_topic"
    UNDETERMINED = "undetermined"


class CriterionAssessmentLabel(StrEnum):
    MET = "met"
    PARTIAL = "partial"
    NOT_OBSERVED = "not_observed"
    UNDETERMINED = "undetermined"


class TargetType(StrEnum):
    CRITERION = "criterion"
    DELIVERY_METRIC = "delivery_metric"


class CoachingAnalyzeRequest(ContractModel):
    """브라우저가 선택할 수 있는 코칭 분석 입력의 전체 범위."""

    action: Literal["analyze"]
    question_id: QuestionId
    answer_revision_id: UUID
    job_snapshot_id: UUID


class AnswerSegment(ContractModel):
    segment_id: NonEmptyText
    text: NonEmptyText


class QuestionContext(ContractModel):
    """서버가 관리하는 질문과 활성 판단 기준."""

    question_id: QuestionId
    text: NonEmptyText
    question_type: NonEmptyText
    active_criterion_ids: Annotated[list[NonEmptyText], Field(min_length=1)]
    criteria_version: NonEmptyText


class PracticeAttemptContext(ContractModel):
    """사용자가 확인한 현재 답변 revision과 전달력 값."""

    answer_revision_id: UUID
    user_id: NonEmptyText
    practice_session_id: UUID
    question_id: QuestionId
    answer_segments: Annotated[list[AnswerSegment], Field(min_length=1)]
    delivery_metrics: dict[NonEmptyText, float | int | None] = Field(
        default_factory=dict
    )
    confirmed_at: datetime
    expires_at: datetime


class JobRequirementContext(ContractModel):
    requirement_id: NonEmptyText
    text: NonEmptyText
    category: Literal["duty", "required", "preferred"]


class JobContext(ContractModel):
    """연습 세션에 고정된 검토 완료 공고 snapshot."""

    job_snapshot_id: UUID
    user_id: NonEmptyText
    practice_session_id: UUID
    source_url: NonEmptyText
    captured_at: datetime
    applicant_context: ApplicantContext | None = None
    supplemental_context: list[dict] = Field(default_factory=list, max_length=60)
    review_status: Literal["reviewed", "pending"]
    requirements: Annotated[list[JobRequirementContext], Field(min_length=1)]
    expires_at: datetime


class CoachingContextBundle(ContractModel):
    question: QuestionContext
    practice_attempt: PracticeAttemptContext
    job_context: JobContext

    def to_validation_context(self) -> "ServerValidationContext":
        return ServerValidationContext(
            requirement_ids=[
                item.requirement_id for item in self.job_context.requirements
            ],
            active_criterion_ids=self.question.active_criterion_ids,
            answer_segments=self.practice_attempt.answer_segments,
            allowed_delivery_metric_ids=list(
                self.practice_attempt.delivery_metrics.keys()
            ),
        )


class ServerValidationContext(ContractModel):
    """LLM이 바꿀 수 없는 서버 보유 ID와 현재 답변 문장."""

    requirement_ids: Annotated[list[NonEmptyText], Field(min_length=1)]
    active_criterion_ids: Annotated[list[NonEmptyText], Field(min_length=1)]
    answer_segments: Annotated[list[AnswerSegment], Field(min_length=1)]
    allowed_delivery_metric_ids: list[NonEmptyText] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_duplicate_server_ids(self) -> Self:
        fields = {
            "requirement_ids": self.requirement_ids,
            "active_criterion_ids": self.active_criterion_ids,
            "answer_segments.segment_id": [
                segment.segment_id for segment in self.answer_segments
            ],
            "allowed_delivery_metric_ids": self.allowed_delivery_metric_ids,
        }
        duplicated = [
            name for name, values in fields.items() if len(values) != len(set(values))
        ]
        if duplicated:
            raise ValueError(
                f"서버 컨텍스트에 중복 ID가 있습니다: {', '.join(duplicated)}"
            )
        return self


class EvidenceQuote(ContractModel):
    segment_id: NonEmptyText
    quote: NonEmptyText


class JobAlignment(ContractModel):
    requirement_id: NonEmptyText
    label: JobAlignmentLabel
    reason: NonEmptyText
    evidence: list[EvidenceQuote]

    @model_validator(mode="after")
    def require_evidence_when_related(self) -> Self:
        if self.label is JobAlignmentLabel.RELATED and not self.evidence:
            raise ValueError("related 공고 관련성에는 evidence가 1개 이상 필요합니다")
        return self


class IntentAssessment(ContractModel):
    label: IntentLabel
    reason: NonEmptyText


class CriterionAssessment(ContractModel):
    criterion_id: NonEmptyText
    assessment: CriterionAssessmentLabel
    reason: NonEmptyText
    # 부재·미확인 판정도 원문 근거를 인용할 수 있다. 원문/ID는 서버 검증.
    evidence: list[EvidenceQuote]
    needed: NonEmptyText | None

    @model_validator(mode="after")
    def enforce_assessment_consistency(self) -> Self:
        if self.assessment is CriterionAssessmentLabel.MET:
            if not self.evidence:
                raise ValueError("met 판정에는 evidence가 1개 이상 필요합니다")
            if self.needed is not None:
                raise ValueError("met 판정의 needed는 null이어야 합니다")
            return self

        if self.needed is None:
            raise ValueError(
                "partial, not_observed, undetermined 판정에는 needed가 필요합니다"
            )

        if self.assessment is CriterionAssessmentLabel.PARTIAL and not self.evidence:
            raise ValueError("partial 판정에는 evidence가 1개 이상 필요합니다")

        return self


class NextAction(ContractModel):
    target_type: TargetType
    target_id: NonEmptyText
    action: NonEmptyText


class CoachingLLMOutput(ContractModel):
    """LLM이 한 번의 생성으로 반환해야 하는 내부 계약."""

    job_alignment: Annotated[list[JobAlignment], Field(min_length=1)]
    intent_assessment: IntentAssessment
    criterion_assessments: Annotated[
        list[CriterionAssessment], Field(min_length=1)
    ]
    clarifying_question: NonEmptyText | None
    next_actions: Annotated[list[NextAction], Field(min_length=1, max_length=2)]
    example_answer: ExampleAnswerText


class ConsolidatedEvidence(ContractModel):
    """서버가 항목별 인용을 한 목록으로 연결한 값."""

    source_type: Literal["job_alignment", "criterion_assessment"]
    source_id: NonEmptyText
    segment_id: NonEmptyText
    quote: NonEmptyText
    reason: NonEmptyText


class Gap(ContractModel):
    """서버가 미충족 기준 판정에서 계산한 부족 항목."""

    criterion_id: NonEmptyText
    assessment: Literal["partial", "not_observed", "undetermined"]
    reason: NonEmptyText
    needed: NonEmptyText


class CoachingResponse(ContractModel):
    """검증을 마친 뒤 사용자 API가 반환하는 핵심 필드."""

    status: CoachingStatus
    job_alignment: list[JobAlignment] = Field(default_factory=list)
    intent_assessment: IntentAssessment
    criterion_assessments: list[CriterionAssessment] = Field(default_factory=list)
    evidence: list[ConsolidatedEvidence] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    clarifying_question: NonEmptyText | None = None
    next_actions: Annotated[list[NextAction], Field(max_length=2)] = Field(
        default_factory=list
    )
    example_answer: ExampleAnswerText | None = None

    @model_validator(mode="after")
    def enforce_status_shape(self) -> Self:
        if self.status in {CoachingStatus.UNSUPPORTED, CoachingStatus.UNAVAILABLE}:
            if any(
                (
                    self.job_alignment,
                    self.criterion_assessments,
                    self.evidence,
                    self.gaps,
                    self.next_actions,
                )
            ):
                raise ValueError(
                    "unsupported/unavailable 응답의 판정·근거·부족 항목·행동은 비어야 합니다"
                )
            if self.intent_assessment.label is not IntentLabel.UNDETERMINED:
                raise ValueError(
                    "unsupported/unavailable 응답의 intent_assessment는 undetermined여야 합니다"
                )
            if self.clarifying_question is not None:
                raise ValueError(
                    "unsupported/unavailable 응답의 clarifying_question은 null이어야 합니다"
                )
            if self.example_answer is not None:
                raise ValueError(
                    "unsupported/unavailable 응답의 example_answer는 null이어야 합니다"
                )
            return self

        if not self.next_actions:
            raise ValueError("ok/needs_more_info 응답에는 next_actions가 1개 이상 필요합니다")
        if self.example_answer is None:
            raise ValueError("ok/needs_more_info 응답에는 example_answer가 필요합니다")
        return self


class TerminalResponseReason(ContractModel):
    status: Literal[CoachingStatus.UNSUPPORTED, CoachingStatus.UNAVAILABLE]
    reason: NonEmptyText
