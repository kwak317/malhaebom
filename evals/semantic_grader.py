"""사람 검토 점수와 자동 정책 검사를 분리한다. 모델 호출 없음."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ReasonAnnotation(StrictModel):
    required_points: list[str] = Field(min_length=1)
    forbidden_conclusions: list[str]
    support_segment_ids: list[str] = Field(min_length=1)


class ActionAnnotation(StrictModel):
    acceptable_targets: list[str]
    priority_targets: list[str]
    forbidden_instructions: list[str]


class QuestionAnnotation(StrictModel):
    policy: Literal['required', 'optional', 'none']
    acceptable_targets: list[str]


class HallucinationAnnotation(StrictModel):
    supported_facts: list[str]
    explicit_negations: list[str]
    forbidden_claims: list[str]


class SemanticAnnotation(StrictModel):
    reason: ReasonAnnotation
    action: ActionAnnotation
    clarifying_question: QuestionAnnotation
    hallucination: HallucinationAnnotation


class SemanticReview(StrictModel):
    reviewer: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    scores: dict[Literal['reason', 'action', 'clarifying_question', 'hallucination'],
                 StrictInt] = Field(default_factory=dict)
    critical_failure: bool | None = None
    critical_failure_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_scores(self):
        if any(type(v) is not int or v not in (0, 1, 2) for v in self.scores.values()):
            raise ValueError('semantic 점수는 0/1/2 정수여야 합니다')
        if self.critical_failure is True and not self.critical_failure_reasons:
            raise ValueError('critical failure 판정 이유가 필요합니다')
        return self


SEMANTIC_RUBRIC = {
    'reason': {'0': '원문과 반대이거나 핵심 판단을 근거 없이 확정함',
               '1': '결론은 대체로 타당하나 required_points 일부 누락·근거 연결 부족',
               '2': '핵심 required_points를 모두 짚고 허용 근거로 결론·한계를 설명함'},
    'action': {'0': '금지 지시·날조 권유 또는 사례와 무관한 행동',
               '1': '허용 대상이나 우선 문제를 놓치거나 실행 지시가 추상적임',
               '2': '우선 대상을 다루고 원문에 맞는 실행 가능한 구체적 행동을 제시함'},
    'clarifying_question': {'0': 'required 질문 누락, none에서 불필요한 질문, 금지 전제 포함',
                           '1': '허용 대상 질문이나 이미 알려진 정보를 반복하거나 범위가 모호함',
                           '2': 'required는 필요한 허용 대상을 묻고, optional은 필요에 맞게 질문·생략하며 none은 생략함'},
    'hallucination': {'0': '없는 사실·성과를 확정하거나 explicit_negations를 뒤집음',
                      '1': '허위 사실 확정은 없으나 추정을 사실과 충분히 구분하지 않거나 범위를 과장함',
                      '2': 'supported_facts 범위에서 사실·추정·제안을 구분하고 명시적 부정을 보존함'},
}


def evaluate_semantic(case, output=None, review=None):
    annotation = case.expected.semantic
    review = SemanticReview.model_validate(review) if review is not None else None
    if review and review.scores and annotation is None:
        raise ValueError('annotation 없는 사례에 semantic 점수를 부여할 수 없습니다')
    checks = {}
    if annotation and isinstance(output, dict):
        question = output.get('clarifying_question')
        policy = annotation.clarifying_question.policy
        checks['question_presence'] = (question is not None if policy == 'required' else
                                       question is None if policy == 'none' else None)
        actions = output.get('next_actions')
        if isinstance(actions, list):
            checks['action_targets'] = bool(actions) and all(
                isinstance(a, dict) and a.get('target_type') == 'criterion' and
                a.get('target_id') in annotation.action.acceptable_targets for a in actions)
    return {'annotated': annotation is not None,
            'rubric': annotation.model_dump() if annotation else None,
            'critical_failure_conditions': case.expected.critical_failure_conditions,
            'scoring_guidelines': SEMANTIC_RUBRIC,
            'automatic_policy_checks': checks,
            'scores': {name: review.scores.get(name) if review else None for name in
                       ('reason', 'action', 'clarifying_question', 'hallucination')},
            'critical_failure': review.critical_failure if review else None,
            'review': review.model_dump() if review else None}


def summarize_semantic(evaluations):
    metrics = {}
    for name in ('reason', 'action', 'clarifying_question', 'hallucination'):
        values = [e['scores'][name] for e in evaluations if e['scores'][name] is not None]
        metrics[name] = {'reviewed': len(values), 'mean': sum(values) / len(values) if values else None}
    critical = [e['critical_failure'] for e in evaluations if e['critical_failure'] is not None]
    return {'annotated': sum(e['annotated'] for e in evaluations), 'semantic': metrics,
            'critical_failure_reviewed': len(critical), 'critical_failure_count': sum(critical),
            'critical_failure_rate': sum(critical) / len(critical) if critical else None}
