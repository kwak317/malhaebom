"""인증된 준비/1차 코칭 대화 API. 모델·서버 판단·저장 실패를 구분한다."""
from __future__ import annotations
import time
import os
import logging
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.auth import AuthenticatedUser
from app.core.supabase_settings import SupabaseSettings
from app.schemas.applicant_context import ApplicantContext
from app.schemas.preparation_conversation import PreparationConversationOutput
from app.services.coaching_observability import CoachingObservation, observation_identity, activate_coaching_trace, active_coaching_trace, reset_coaching_trace, set_active_coaching_identity
from app.services.coaching_runtime import OpenAICompatibleJsonProvider
from app.services.preparation_conversation_generation import preparation_output_schema
from app.services.preparation_conversation_policy import PreparationPolicyError
from app.services.preparation_conversation_repository import PreparationRepository, PreparationConflict
from app.services.preparation_conversation_runtime import PreparationConversationService, PROMPT_VERSION, SKILL_VERSION, load_preparation_prompt
from app.services.free_chat import FreeChatDispatcher, FreeChatOutput, free_chat_output_schema, MODEL as FREE_CHAT_MODEL, PROMPT_VERSION as FREE_CHAT_PROMPT_VERSION
from app.services.supabase_persistence import SupabasePersistenceError
from app.services.preparation_selection_actions import SelectionSnapshot


class PreparationSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_posting_id: UUID | None = None
    requirement_ids: list[UUID] = Field(default_factory=list, max_length=2)
    question_id: str | None = Field(default=None, min_length=1, max_length=100)
    custom_question_text: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_choices(self):
        checked = SelectionSnapshot.model_validate(self.model_dump())
        self.custom_question_text = checked.custom_question_text
        return self


class RestartConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: UUID
    confirm: bool


class PreparationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    conversation_id: UUID | None = None
    practice_session_id: UUID | None = None
    current_stage: Literal["ncs", "readme", "resume", "first_coaching"]
    message: str = Field(min_length=1, max_length=2000)
    review_context: ApplicantContext | None = None
    selection: PreparationSelection | None = None
    selection_revision: int | None = Field(default=None, ge=0)
    restart_target: Literal["ncs", "resume", "readme", "jobs", "questions"] | None = None
    restart_confirmation: RestartConfirmation | None = None
    ui_context: Literal["ncs", "ncs_review", "resume", "resume_review", "readme", "readme_review", "jobs", "requirements", "questions", "first_coaching"] | None = None


class PreparationResponse(BaseModel):
    conversation_id: UUID
    message: str
    follow_up_question: str | None
    action: Literal["stay", "request_rerecord", "selection_updated", "practice_restarted"]
    status: Literal["ok", "unavailable"]
    selection_state: SelectionSnapshot | None = None
    selection_revision: int | None = None
    execution_result: Literal["verified", "awaiting_confirmation", "failed"] | None = None
    selection_job: dict | None = None
    restart: dict | None = None


class PreparationBindRequest(BaseModel):
    conversation_id: UUID
    practice_session_id: UUID


class PreparationHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    message: str
    follow_up_question: str | None = None


class PreparationHistoryResponse(BaseModel):
    messages: list[PreparationHistoryMessage]


def register_preparation_routes(app, require_authenticated_user):
    provider = getattr(app.state.coaching_service, "provider", None)
    service = None
    if os.getenv("PREPARATION_CONVERSATION_ENABLED") == "true" and isinstance(provider, OpenAICompatibleJsonProvider):
        try:
            settings = SupabaseSettings.from_env(require_service_role=True)
            free_chat_enabled = os.getenv("FREE_CHAT_ENABLED") == "true"
            chat = OpenAICompatibleJsonProvider(api_key=provider.api_key,
                model_name=FREE_CHAT_MODEL if free_chat_enabled else "google/gemini-3.5-flash-lite", base_url=provider.base_url,
                max_tokens=2200, max_transport_attempts=1, observation_sink=None,
                prompt_version=PROMPT_VERSION, skill_version=SKILL_VERSION)
            def generate_schema(system, context, schema, max_tokens=2200):
                import json
                return chat.client.chat.completions.create(model=chat.model_name,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
                    response_format={"type": "json_schema", "json_schema": {
                        "name": "malhaebom_preparation_conversation", "strict": True,
                        "schema": schema}},
                    max_tokens=max_tokens, extra_body={"provider": {"require_parameters": True}}).model_dump()
            def generate(system, context):
                return generate_schema(system, context, preparation_output_schema(context))
            free_chat = FreeChatDispatcher(lambda system, context: generate_schema(
                system, context, free_chat_output_schema(context), max_tokens=3200),
                observation_sink=app.state.coaching_observation_sink) if free_chat_enabled else None
            service = PreparationConversationService(PreparationRepository(settings), generate,
                system_prompt=load_preparation_prompt(getattr(app.state.coaching_observation_sink, "client", None)),
                observation_sink=app.state.coaching_observation_sink, free_chat=free_chat,
                model_name=chat.model_name)
        except (ValueError, OSError) as error:
            logging.getLogger(__name__).warning("Preparation startup failed: %s", type(error).__name__)
    app.state.preparation_conversation_service = service

    @app.get("/practice-records/{session_id}/preparation-chat", response_model=PreparationHistoryResponse)
    def preparation_history(session_id: UUID, user: AuthenticatedUser = Depends(require_authenticated_user)):
        active = app.state.preparation_conversation_service
        if active is None:
            raise HTTPException(status_code=503, detail="채팅 내역을 불러올 수 없습니다.")
        try:
            return {"messages": active.repository.history(user, session_id)}
        except KeyError:
            raise HTTPException(status_code=404, detail="연습 기록을 찾을 수 없습니다.") from None
        except SupabasePersistenceError:
            raise HTTPException(status_code=503, detail="채팅 내역을 불러오지 못했습니다.") from None

    @app.post("/api/agent/preparation", response_model=PreparationResponse)
    def preparation(request: PreparationRequest, user: AuthenticatedUser = Depends(require_authenticated_user)):
        active = app.state.preparation_conversation_service
        if active is None:
            raise HTTPException(503, "준비 대화 서비스를 실행할 설정이 필요합니다.")
        started = time.perf_counter()
        outcome = "error"
        trace, trace_token = active_coaching_trace(), None
        if trace is None:
            trace, trace_token = activate_coaching_trace()
        set_active_coaching_identity(user_key=observation_identity(user.user_id),
            session_key=observation_identity(str(request.conversation_id or request.request_id)))
        try:
            result = active.respond(user, request)
            outcome = result["status"]
            return result
        except KeyError:
            raise HTTPException(404, "유효한 대화 또는 연습 기록을 찾을 수 없습니다.") from None
        except PreparationConflict as error:
            detail = str(error)
            if request.conversation_id and hasattr(active, "selection_recovery"):
                try:
                    recovered = active.selection_recovery(user, request.conversation_id)
                    if recovered:
                        detail = {"message": detail, "code": "selection_conflict", **recovered}
                except (KeyError, ValueError, PreparationConflict, SupabasePersistenceError):
                    pass
            raise HTTPException(409, detail) from None
        except PreparationPolicyError:
            raise HTTPException(502, "응답 내용을 확인하지 못했어요. 현재 내용을 유지했으니 다시 보내 주세요.") from None
        except SupabasePersistenceError:
            raise HTTPException(503, "대화 상태를 저장하거나 불러오지 못했어요. 다시 시도해 주세요.") from None
        finally:
            try:
                app.state.coaching_observation_sink.record(CoachingObservation(
                    trace_name="preparation.chat", trace_id=trace.trace_id,
                    input_tokens=trace.input_tokens if trace.has_input_tokens else None,
                    output_tokens=trace.output_tokens if trace.has_output_tokens else None,
                    cost_usd=trace.cost_usd if trace.has_cost else None, user_key=observation_identity(user.user_id),
                    session_key=observation_identity(str(request.conversation_id or request.request_id)),
                    model=active.model_name, prompt_version=(FREE_CHAT_PROMPT_VERSION + "+" + PROMPT_VERSION) if active.free_chat else PROMPT_VERSION,
                    skill_version=SKILL_VERSION, status=outcome,
                    latency_ms=(time.perf_counter() - started) * 1000))
            except Exception:
                pass
            if trace_token is not None:
                reset_coaching_trace(trace_token)

    @app.post("/api/agent/preparation/bind", status_code=204)
    def preparation_bind(request: PreparationBindRequest, user: AuthenticatedUser = Depends(require_authenticated_user)):
        active = app.state.preparation_conversation_service
        if active is None:
            raise HTTPException(503, "준비 대화 서비스를 실행할 설정이 필요합니다.")
        try:
            active.bind(user, request.conversation_id, request.practice_session_id)
        except KeyError:
            raise HTTPException(404, "유효한 대화 또는 연습 기록을 찾을 수 없습니다.") from None
        except PreparationConflict as error:
            raise HTTPException(409, str(error)) from None
        except SupabasePersistenceError:
            raise HTTPException(503, "대화 자료를 연습에 연결하지 못했어요. 다시 시도해 주세요.") from None
