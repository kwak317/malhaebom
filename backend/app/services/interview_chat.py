"""사용자 소유 기록에 연결한 비교 후 면접 대화. 완료 대화를 저장하되 원래 답변·코칭은 변경하지 않는다."""
from __future__ import annotations

import json
import os
from app.services.preparation_conversation_repository import confirmed_context, supplemental_context_path
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock, RLock
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.core.auth import AuthenticatedUser
from app.schemas.applicant_context import ApplicantContext, APPLICANT_CONTEXT_GUIDANCE
from app.schemas.interview_chat import (
    InterviewChatHistory, InterviewChatHistoryMessage, InterviewChatOutput,
    InterviewChatRequest, InterviewChatResponse,
)
from app.services.prompt_templates import compose_skill_prompt, load_prompt_template
from app.services.coaching_questions import get_preset_coaching_question
from app.services.coaching_runtime import CoachingProviderResult, OpenAICompatibleJsonProvider
from app.services.practice_history import PracticeHistoryService, coaching_content_analysis_from_response
from app.services.supabase_persistence import SupabaseAnalysisRepository
from services.llm import OutputContractError

RECENT_MESSAGES = 12
PROMPT = compose_skill_prompt(
    load_prompt_template("interview-conversation.md"),
    skill_text=(Path(__file__).resolve().parents[3] / "skills/interview-conversation/SKILL.md").read_text(encoding="utf-8"),
    skill_version="interview-conversation-v2", prompt_version="interview-conversation-output-v1",
)


class InterviewChatConflict(ValueError):
    pass


def _expiry(value: object) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is None or result <= datetime.now(UTC):
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise KeyError("expired-context") from None


class InterviewChatContextRepository(SupabaseAnalysisRepository):
    def load(self, user: AuthenticatedUser, session_id: UUID) -> tuple[dict[str, Any], datetime, tuple[str, ...]]:
        sid = quote(str(session_id), safe="")
        response = self._request("GET", "/rest/v1/practice_sessions"
            f"?id=eq.{sid}&select=id,user_id,question_id,expires_at,applicant_context,"
            "job_postings(company,title,source_url,review_status),"
            "practice_session_requirements(job_requirements(code,requirement_text,source_excerpt))", user=user)
        sessions = response.json()
        if not isinstance(sessions, list) or not sessions or sessions[0].get("user_id") != user.user_id:
            raise KeyError(str(session_id))
        session = sessions[0]
        expiry = _expiry(session.get("expires_at"))
        question = get_preset_coaching_question(str(session.get("question_id")))
        if question is None:
            raise InterviewChatConflict("기본 질문의 1·2차 코칭을 완료한 뒤 대화를 시작해 주세요.")
        posting = session.get("job_postings")
        if not isinstance(posting, dict) or posting.get("review_status") != "reviewed":
            raise InterviewChatConflict("선택 공고의 검토 상태를 확인할 수 없습니다.")
        rows = self.get_completed_session_jobs(user, str(session_id))
        if len(rows) != 2 or {row.get("attempt_no") for row in rows} != {1, 2}:
            raise InterviewChatConflict("1·2차 답변을 모두 완료한 뒤 대화를 시작해 주세요.")
        fingerprint = []
        versions = set()
        for row in sorted(rows, key=lambda item: item["attempt_no"]):
            if row.get("user_id") != user.user_id or row.get("question_id") != question.question_id:
                raise KeyError(str(session_id))
            expiry = min(expiry, _expiry(row.get("expires_at")))
            revisions = row.get("answer_revisions") or []
            if not revisions:
                raise InterviewChatConflict("두 답변의 전사문 확인과 코칭을 먼저 완료해 주세요.")
            revision = max(revisions, key=lambda item: item["confirmed_at"])
            expiry = min(expiry, _expiry(revision.get("expires_at")))
            runs = revision.get("coaching_runs") or []
            if not runs:
                raise InterviewChatConflict("두 답변의 코칭을 먼저 완료해 주세요.")
            run = max(runs, key=lambda item: item["created_at"])
            expiry = min(expiry, _expiry(run.get("expires_at")))
            if not coaching_content_analysis_from_response(run.get("response"), revision.get("confirmed_text", "")):
                raise InterviewChatConflict("두 답변의 코칭을 먼저 완료해 주세요.")
            version = tuple(run.get(name) for name in ("model_name", "prompt_version", "skill_version", "criteria_version"))
            if any(not isinstance(value, str) or not value.strip() for value in version):
                raise InterviewChatConflict("두 답변의 코칭 버전을 확인할 수 없습니다. 같은 기준으로 다시 분석해 주세요.")
            if run["criteria_version"] != question.criteria_version:
                raise InterviewChatConflict("현재 질문과 답변의 코칭 기준 버전이 다릅니다. 다시 분석해 주세요.")
            versions.add(version)
            fingerprint.extend([str(revision["id"]), str(run["created_at"]), *version])
        if len(versions) != 1:
            raise InterviewChatConflict("두 답변의 코칭 기준 버전이 다릅니다. 같은 기준으로 다시 분석해 주세요.")
        # 기존 서버 비교 계산과 사용자 확정 전사문을 그대로 재사용한다.
        record = PracticeHistoryService(_RowsRepository(rows)).get_record(user, str(session_id))
        if not record.get("comparison", {}).get("content_available"):
            raise InterviewChatConflict("두 답변의 내용 비교를 준비하지 못했습니다. 코칭 결과를 확인해 주세요.")
        active = set(question.active_criterion_ids)
        compared = {item["criterion_id"] for item in record["comparison"]["criteria"]}
        if compared != active:
            raise InterviewChatConflict("현재 질문과 답변의 코칭 기준이 다릅니다.")
        requirements = [item["job_requirements"] for item in session.get("practice_session_requirements", [])
                        if isinstance(item.get("job_requirements"), dict)]
        if not 1 <= len(requirements) <= 2:
            raise InterviewChatConflict("선택한 공고 요구사항을 확인할 수 없습니다.")
        supplemental = (confirmed_context(self._request("GET", supplemental_context_path(session_id, user.user_id), user=user).json())
            if os.getenv("PREPARATION_CONVERSATION_ENABLED") == "true" else [])
        return {"question": question.model_dump(mode="json"), "job": posting,
                "requirements": requirements, "attempts": record["attempts"],
                "comparison": record["comparison"], "supplemental_context": supplemental,
                "applicant_context": (ApplicantContext.model_validate(session["applicant_context"]).model_context()
                    if session.get("applicant_context") is not None else None)}, expiry, tuple(fingerprint)

    def get_completed_session_jobs(self, user, practice_session_id):
        sid = quote(practice_session_id, safe="")
        now = quote(datetime.now(UTC).isoformat(), safe="")
        response = self._request("GET", "/rest/v1/analysis_jobs"
            f"?practice_session_id=eq.{sid}&status=eq.completed&expires_at=gt.{now}"
            "&select=*,answer_revisions(id,confirmed_text,confirmed_at,expires_at,delivery_metrics,"
            "coaching_runs(response,created_at,expires_at,model_name,prompt_version,skill_version,criteria_version))&order=attempt_no.asc", user=user)
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            raise KeyError(practice_session_id)
        return rows


    def save_history(self, user: AuthenticatedUser, session_id: UUID, history: InterviewChatHistory) -> None:
        context, expiry, fingerprint = self.load(user, session_id)
        if tuple(history.fingerprint) != fingerprint:
            raise InterviewChatConflict("답변이 변경되었습니다. 비교 결과에서 새 대화를 시작해 주세요.")
        history.expires_at = min(history.expires_at, expiry)
        _expiry(history.expires_at)
        second = next(item for item in context["attempts"] if item["attempt_no"] == 2)
        now = quote(datetime.now(UTC).isoformat(), safe="")
        path = ("/rest/v1/analysis_jobs"
                f"?id=eq.{quote(second['job_id'], safe='')}&practice_session_id=eq.{session_id}"
                f"&user_id=eq.{quote(user.user_id, safe='')}&attempt_no=eq.2"
                f"&status=eq.completed&expires_at=gt.{now}")
        rows = self._request("GET", path + "&select=id,user_id,result", user=user).json()
        if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("user_id") != user.user_id:
            raise KeyError(str(session_id))
        original_result = rows[0].get("result")
        if not isinstance(original_result, dict):
            raise KeyError(str(session_id))
        updated = self._request("PATCH", path, user=user, headers={"Prefer": "return=representation"},
            json={"result": {**original_result, "interview_chat": history.model_dump(mode="json")}}).json()
        if not isinstance(updated, list) or len(updated) != 1 or updated[0].get("id") != second["job_id"]:
            raise KeyError(str(session_id))


class _RowsRepository:
    def __init__(self, rows):
        self.rows = rows

    def get_completed_session_jobs(self, *_):
        return self.rows


@dataclass
class Conversation:
    conversation_id: UUID
    expires_at: datetime
    fingerprint: tuple[str, ...]
    start_request_id: UUID
    messages: list[dict[str, str]] = field(default_factory=list)
    history_messages: list[InterviewChatHistoryMessage] = field(default_factory=list)
    finished_history: InterviewChatHistory | None = None
    history_saved: bool = False
    memory: str = ""
    last_response: InterviewChatResponse | None = None
    completed_requests: dict[UUID, tuple[tuple[str, str | None], InterviewChatResponse]] = field(default_factory=dict)
    lock: Any = field(default_factory=Lock)


class InterviewChatService:
    def __init__(self, repository, provider):
        self.repository = repository
        self.provider = provider
        self.conversations: dict[tuple[str, UUID], Conversation] = {}
        self.lock = RLock()

    def respond(self, user: AuthenticatedUser, request: InterviewChatRequest) -> InterviewChatResponse:
        key = (user.user_id, request.practice_session_id)
        try:
            context, expires_at, fingerprint = self.repository.load(user, request.practice_session_id)
        except KeyError:
            with self.lock:
                self.conversations.pop(key, None)
            raise
        with self.lock:
            for old_key, old in list(self.conversations.items()):
                if old.expires_at <= datetime.now(UTC):
                    self.conversations.pop(old_key, None)
            state = self.conversations.get(key)
            if request.action == "start" and (state is None or state.start_request_id != request.request_id):
                if state and request.request_id in state.completed_requests:
                    raise InterviewChatConflict("같은 요청 ID에 다른 메시지를 사용할 수 없습니다.")
                state = Conversation(uuid4(), expires_at, fingerprint, request.request_id)
                self.conversations[key] = state
            if state is None or (request.action != "start" and state.conversation_id != request.conversation_id):
                raise KeyError("conversation-not-found")
            state.expires_at = min(state.expires_at, expires_at)
            if fingerprint != state.fingerprint:
                self.conversations.pop(key, None)
                raise InterviewChatConflict("답변이 변경되었습니다. 비교 결과에서 새 대화를 시작해 주세요.")
        if not state.lock.acquire(blocking=False):
            raise InterviewChatConflict("이전 대화 요청을 처리하고 있어요. 잠시 뒤 다시 시도해 주세요.")
        try:
            signature = (request.action, request.message)
            cached = state.completed_requests.get(request.request_id)
            if cached:
                if cached[0] != signature:
                    raise InterviewChatConflict("같은 요청 ID에 다른 메시지를 사용할 수 없습니다.")
                self._save_finished(user, request.practice_session_id, state)
                return cached[1]
            if state.last_response and state.last_response.status == "finished":
                if request.action == "finish":
                    state.completed_requests[request.request_id] = (signature, state.last_response)
                    self._save_finished(user, request.practice_session_id, state)
                    return state.last_response
                raise InterviewChatConflict("이미 마친 대화입니다.")
            prompt = json.dumps({"action": request.action, "practice_context": context,
                "previous_conversation_summary": state.memory, "recent_messages": state.messages,
                "user_message": request.message,
                "response_requirements": {"answer_known_information_first": True,
                    "include_requested_result_in_message": True, "do_not_only_announce_future_help": True,
                    "summary_may_be_requested_while_active": request.action == "message",
                    "only_finish_action_ends_conversation": True}}, ensure_ascii=False)
            if context.get("applicant_context") is not None or context.get("supplemental_context"):
                prompt = APPLICANT_CONTEXT_GUIDANCE + prompt
            output = self._generate(prompt, request.action)
            _expiry(state.expires_at)
            result = InterviewChatResponse(conversation_id=state.conversation_id,
                status="finished" if request.action == "finish" else "active",
                message=output.message, follow_up_question=output.follow_up_question, summary=output.summary)
            if request.message:
                state.messages.append({"role": "user", "content": request.message})
                state.history_messages.append(InterviewChatHistoryMessage(role="user", message=request.message))
            elif request.action == "finish":
                state.history_messages.append(InterviewChatHistoryMessage(role="user", message="연습 마치기"))
            state.messages.append({"role": "assistant", "content": output.message + ("\n" + output.follow_up_question if output.follow_up_question else "")})
            state.history_messages.append(InterviewChatHistoryMessage(role="assistant", message=output.message,
                follow_up_question=output.follow_up_question, summary=output.summary))
            state.messages = state.messages[-RECENT_MESSAGES:]
            state.memory = output.memory
            state.last_response = result
            state.completed_requests[request.request_id] = (signature, result)
            if request.action == "finish":
                state.finished_history = InterviewChatHistory(conversation_id=state.conversation_id,
                    completed_at=datetime.now(UTC), expires_at=state.expires_at,
                    fingerprint=list(state.fingerprint), messages=state.history_messages)
                self._save_finished(user, request.practice_session_id, state)
            return result
        finally:
            state.lock.release()

    def _save_finished(self, user: AuthenticatedUser, session_id: UUID, state: Conversation) -> None:
        if state.finished_history is not None and not state.history_saved:
            # 생성 응답을 먼저 캐시한다. 저장 실패 재시도는 모델/메시지를 중복 생성하지 않는다.
            self.repository.save_history(user, session_id, state.finished_history)
            state.history_saved = True

    def _generate(self, prompt: str, action: str) -> InterviewChatOutput:
        repair = ""
        for attempt in range(2):
            try:
                value = self.provider.generate(system_prompt=PROMPT, user_prompt=prompt + repair,
                    schema=InterviewChatOutput.model_json_schema())
                if isinstance(value, CoachingProviderResult):
                    value = value.output
                output = InterviewChatOutput.model_validate(value)
                if action == "start" and output.follow_up_question is None:
                    raise ValueError("시작에는 첫 질문 하나가 필요합니다.")
                if action == "finish" and output.summary is None:
                    raise ValueError("종료 요청에는 요약이 필요합니다.")
                if action == "start" and output.summary is not None:
                    raise ValueError("시작 요청에는 종료 요약을 작성하지 않습니다.")
                if action == "finish" and output.follow_up_question is not None:
                    raise ValueError("종료에는 꼬리질문을 하지 않습니다.")
                return output
            except (ValidationError, ValueError, OutputContractError) as error:
                if attempt == 1:
                    raise OutputContractError(["면접 대화 출력 계약 검증 실패"]) from None
                detail = "JSON 필드와 action에 맞는 종료 요약 규칙을 확인하세요."
                if isinstance(error, ValidationError):
                    detail = "; ".join(".".join(map(str, item["loc"])) + ": " + item["msg"]
                        for item in error.errors(include_input=False, include_url=False)[:3])
                repair = ("\n출력 계약 검증 오류: " + detail
                    + " message에는 질문이나 물음표를 쓰지 말고 서술문만 쓰세요. 질문은 follow_up_question에만 하나 작성하세요. action과 JSON 스키마를 지켜 전체 JSON을 다시 작성하세요.")
        raise AssertionError("unreachable")


def build_interview_chat_service(coaching_service, analysis_service) -> InterviewChatService | None:
    provider = getattr(coaching_service, "provider", None)
    repository = getattr(analysis_service, "repository", None)
    if not isinstance(provider, OpenAICompatibleJsonProvider) or repository is None:
        return None
    chat_provider = OpenAICompatibleJsonProvider(api_key=provider.api_key, model_name=provider.model_name,
        base_url=provider.base_url, timeout_seconds=provider.http.timeout.read or 25.0,
        schema_name="malhaebom_interview_conversation", require_provider_parameters=provider.require_provider_parameters,
        max_tokens=2048)
    return InterviewChatService(InterviewChatContextRepository(repository.settings), chat_provider)
