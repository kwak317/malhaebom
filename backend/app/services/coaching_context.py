"""서버 소유 코칭 문맥 조회와 model-free thin slice."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.core.auth import AuthenticatedUser
from app.schemas.coaching import (
    CoachingAnalyzeRequest,
    CoachingContextBundle,
    CoachingResponse,
    JobContext,
    JobRequirementContext,
    PracticeAttemptContext,
    QuestionContext,
)
from app.services.coaching_skill import (
    CoachingSkillError,
    SkillBundle,
    load_skill_bundle,
)
from app.services.coaching_questions import is_custom_coaching_question_id
from services.llm import validate_and_build_response


DEMO_ANSWER_REVISION_ID = UUID("00000000-0000-0000-0000-000000000101")
DEMO_JOB_SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000201")
DEMO_PRACTICE_SESSION_ID = UUID("00000000-0000-0000-0000-000000000301")
DEMO_QUESTION_ID = "preset-04"


class CoachingContextNotFound(KeyError):
    """없는·다른 사용자·만료 레코드를 외부에서 구분하지 않는 오류."""


class CoachingContextConflict(ValueError):
    """소유한 레코드 사이의 질문·세션·검토 상태가 일치하지 않는 오류."""


class CoachingContextRepository(Protocol):
    def get_question(self, question_id: str) -> QuestionContext | None: ...

    def get_custom_question(self, attempt: PracticeAttemptContext) -> QuestionContext | None: ...

    def get_practice_attempt(
        self, answer_revision_id: UUID
    ) -> PracticeAttemptContext | None: ...

    def get_job_context(
        self, job_snapshot_id: UUID, practice_session_id: UUID
    ) -> JobContext | None: ...


class InMemoryCoachingContextRepository:
    """서버 소유 fixture를 사용하는 model-free 개발 저장소."""

    def __init__(
        self,
        *,
        questions: list[QuestionContext],
        practice_attempts: list[PracticeAttemptContext],
        job_contexts: list[JobContext],
    ) -> None:
        self.questions = {item.question_id: item for item in questions}
        self.practice_attempts = {
            item.answer_revision_id: item for item in practice_attempts
        }
        self.job_contexts = {
            item.job_snapshot_id: item for item in job_contexts
        }

    def get_question(self, question_id: str) -> QuestionContext | None:
        return self.questions.get(question_id)

    def get_custom_question(self, attempt: PracticeAttemptContext) -> QuestionContext | None:
        return self.questions.get(attempt.question_id)

    def get_practice_attempt(
        self, answer_revision_id: UUID
    ) -> PracticeAttemptContext | None:
        return self.practice_attempts.get(answer_revision_id)

    def get_job_context(
        self, job_snapshot_id: UUID, practice_session_id: UUID
    ) -> JobContext | None:
        return self.job_contexts.get(job_snapshot_id)


class CoachingContextService:
    def __init__(
        self,
        repository: CoachingContextRepository,
        *,
        skill_bundle: SkillBundle | None = None,
    ) -> None:
        self.repository = repository
        self.skill_bundle = skill_bundle or load_skill_bundle()

    def get_question(
        self,
        user: AuthenticatedUser,
        *,
        question_id: str,
        answer_revision_id: UUID,
        now: datetime | None = None,
    ) -> QuestionContext:
        attempt = self.get_practice_attempt(
            user,
            answer_revision_id=answer_revision_id,
            now=now,
        )
        if attempt.question_id != question_id:
            raise CoachingContextConflict("답변 revision의 질문과 요청 질문이 다릅니다.")

        if is_custom_coaching_question_id(question_id):
            question = self.repository.get_custom_question(attempt)
        else:
            question = self.repository.get_question(question_id)
        if question is None:
            raise CoachingContextNotFound(question_id)
        try:
            self.skill_bundle.validate_question_context(question)
        except CoachingSkillError as error:
            raise CoachingContextConflict(str(error)) from error
        return question

    def get_practice_attempt(
        self,
        user: AuthenticatedUser,
        *,
        answer_revision_id: UUID,
        now: datetime | None = None,
    ) -> PracticeAttemptContext:
        attempt = self.repository.get_practice_attempt(answer_revision_id)
        if attempt is None:
            raise CoachingContextNotFound(str(answer_revision_id))
        self._require_owned_and_active(
            record_user_id=attempt.user_id,
            expires_at=attempt.expires_at,
            user=user,
            now=now,
        )
        return attempt

    def get_job_context(
        self,
        user: AuthenticatedUser,
        *,
        job_snapshot_id: UUID,
        answer_revision_id: UUID,
        now: datetime | None = None,
    ) -> JobContext:
        attempt = self.get_practice_attempt(
            user,
            answer_revision_id=answer_revision_id,
            now=now,
        )
        job_context = self.repository.get_job_context(
            job_snapshot_id, attempt.practice_session_id
        )
        if job_context is None:
            raise CoachingContextNotFound(str(job_snapshot_id))
        self._require_owned_and_active(
            record_user_id=job_context.user_id,
            expires_at=job_context.expires_at,
            user=user,
            now=now,
        )
        if job_context.practice_session_id != attempt.practice_session_id:
            raise CoachingContextConflict("답변과 공고 문맥의 연습 세션이 다릅니다.")
        if job_context.review_status != "reviewed":
            raise CoachingContextConflict("검토 완료된 공고 문맥만 사용할 수 있습니다.")
        return job_context

    def load_context(
        self,
        user: AuthenticatedUser,
        request: CoachingAnalyzeRequest,
        *,
        now: datetime | None = None,
    ) -> CoachingContextBundle:
        attempt = self.get_practice_attempt(
            user,
            answer_revision_id=request.answer_revision_id,
            now=now,
        )
        question = self.get_question(
            user,
            question_id=request.question_id,
            answer_revision_id=request.answer_revision_id,
            now=now,
        )
        job_context = self.get_job_context(
            user,
            job_snapshot_id=request.job_snapshot_id,
            answer_revision_id=request.answer_revision_id,
            now=now,
        )
        return CoachingContextBundle(
            question=question,
            practice_attempt=attempt,
            job_context=job_context,
        )

    @staticmethod
    def _require_owned_and_active(
        *,
        record_user_id: str,
        expires_at: datetime,
        user: AuthenticatedUser,
        now: datetime | None,
    ) -> None:
        active_now = now or datetime.now(UTC)
        if record_user_id != user.user_id or expires_at <= active_now:
            raise CoachingContextNotFound()


class MockCoachingService:
    """실제 모델 대신 고정 판정을 현재 출력 계약으로 검증한다."""

    def __init__(self, context_service: CoachingContextService) -> None:
        self.context_service = context_service

    def analyze(
        self, user: AuthenticatedUser, request: CoachingAnalyzeRequest
    ) -> CoachingResponse:
        context = self.context_service.load_context(user, request)
        segment_one, segment_two = context.practice_attempt.answer_segments[:2]

        raw_output = {
            "job_alignment": [
                {
                    "requirement_id": requirement.requirement_id,
                    "label": "related",
                    "reason": "서버 로그 확인과 오류 처리 코드 수정 경험이 요구사항과 관련됩니다.",
                    "evidence": [
                        {
                            "segment_id": segment_two.segment_id,
                            "quote": "서버 로그를 확인하고 토큰 만료 처리 코드를 수정했습니다.",
                        }
                    ],
                }
                for requirement in context.job_context.requirements
            ],
            "intent_assessment": {
                "label": "partial",
                "reason": "문제와 본인 행동은 있으나 선택 이유와 결과 확인이 없습니다.",
            },
            "criterion_assessments": [
                {
                    "criterion_id": "problem_context",
                    "assessment": "met",
                    "reason": "발생한 문제를 설명했습니다.",
                    "evidence": [
                        {
                            "segment_id": segment_one.segment_id,
                            "quote": "로그인 오류가 발생했습니다.",
                        }
                    ],
                    "needed": None,
                },
                {
                    "criterion_id": "cause_observation",
                    "assessment": "partial",
                    "reason": "로그를 확인했다고 했지만 실제로 관찰한 신호가 부족합니다.",
                    "evidence": [
                        {
                            "segment_id": segment_two.segment_id,
                            "quote": "서버 로그를 확인하고",
                        }
                    ],
                    "needed": "로그에서 실제로 관찰한 오류·상태 변화·조건",
                },
                {
                    "criterion_id": "cause_inference",
                    "assessment": "not_observed",
                    "reason": "관찰 신호로 토큰 만료를 원인으로 좁힌 이유를 확인할 수 없습니다.",
                    "evidence": [],
                    "needed": "관찰 신호가 토큰 만료를 원인 후보로 좁힌 이유",
                },
                {
                    "criterion_id": "own_action",
                    "assessment": "met",
                    "reason": "본인이 수행한 수정 행동을 설명했습니다.",
                    "evidence": [
                        {
                            "segment_id": segment_two.segment_id,
                            "quote": "토큰 만료 처리 코드를 수정했습니다.",
                        }
                    ],
                    "needed": None,
                },
                {
                    "criterion_id": "action_rationale",
                    "assessment": "not_observed",
                    "reason": "이 방법을 선택한 이유를 확인할 수 없습니다.",
                    "evidence": [],
                    "needed": "다른 방법보다 토큰 만료 처리를 먼저 수정한 이유",
                },
                {
                    "criterion_id": "result_verification",
                    "assessment": "not_observed",
                    "reason": "수정 후 결과를 확인한 방법이 없습니다.",
                    "evidence": [],
                    "needed": "수정 후 같은 조건에서 확인한 방법과 결과",
                },
            ],
            "clarifying_question": "수정 후 같은 오류가 해결됐는지 어떤 방법으로 확인했나요?",
            "next_actions": [
                {
                    "target_type": "criterion",
                    "target_id": "cause_observation",
                    "action": "로그에서 실제로 본 신호를 한 문장으로 덧붙여 보세요.",
                },
                {
                    "target_type": "criterion",
                    "target_id": "result_verification",
                    "action": "수정 후 확인한 조건과 관찰 결과를 덧붙여 보세요.",
                },
            ],
            "example_answer": (
                "팀 프로젝트에서 로그인 오류가 발생해 저는 서버 로그를 확인하고 "
                "토큰 만료 처리 코드를 수정했습니다. 이후 [실제로 확인한 방법과 결과]를 "
                "덧붙여 해결 여부를 설명하겠습니다."
            ),
        }
        return validate_and_build_response(
            raw_output,
            context.to_validation_context(),
        )


def build_demo_coaching_service(
    user_id: str,
    *,
    now: datetime | None = None,
) -> MockCoachingService:
    """Swagger와 테스트에서 사용하는 명시적 개발 fixture를 만든다."""

    active_now = now or datetime.now(UTC)
    repository = InMemoryCoachingContextRepository(
        questions=[
            QuestionContext(
                question_id=DEMO_QUESTION_ID,
                text="프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
                question_type="problem_solving",
                active_criterion_ids=[
                    "problem_context",
                    "cause_observation",
                    "cause_inference",
                    "own_action",
                    "action_rationale",
                    "result_verification",
                ],
                criteria_version="problem-solving-v4-draft.3",
            )
        ],
        practice_attempts=[
            PracticeAttemptContext(
                answer_revision_id=DEMO_ANSWER_REVISION_ID,
                user_id=user_id,
                practice_session_id=DEMO_PRACTICE_SESSION_ID,
                question_id=DEMO_QUESTION_ID,
                answer_segments=[
                    {
                        "segment_id": "demo-rev1-s1",
                        "text": "팀 프로젝트에서 로그인 오류가 발생했습니다.",
                    },
                    {
                        "segment_id": "demo-rev1-s2",
                        "text": "저는 서버 로그를 확인하고 토큰 만료 처리 코드를 수정했습니다.",
                    },
                ],
                delivery_metrics={"speech_duration_sec": 8.4, "cpm": 285.0},
                confirmed_at=active_now - timedelta(minutes=5),
                expires_at=active_now + timedelta(hours=24),
            )
        ],
        job_contexts=[
            JobContext(
                job_snapshot_id=DEMO_JOB_SNAPSHOT_ID,
                user_id=user_id,
                practice_session_id=DEMO_PRACTICE_SESSION_ID,
                source_url="https://example.invalid/job-snapshot-demo-01",
                captured_at=active_now - timedelta(days=1),
                review_status="reviewed",
                requirements=[
                    JobRequirementContext(
                        requirement_id="J01-R1",
                        text="서버 로그를 활용해 백엔드 오류를 분석하고 개선한 경험",
                        category="required",
                    )
                ],
                expires_at=active_now + timedelta(hours=24),
            )
        ],
    )
    return MockCoachingService(CoachingContextService(repository))
