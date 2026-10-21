from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Literal, Mapping
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.services.loading_progress import install_loading_progress
from app.services.request_trace import register_chat_request_tracing, record_request_link, TRACE_HEADERS
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse

from app.core.auth import (
    AuthenticatedUser,
    SupabaseJwtVerifier,
    build_access_token_verifier_from_env,
    create_require_authenticated_user,
)
from app.schemas.errors import (
    ApiErrorDetail,
    ApiErrorResponse,
    FailureState,
    api_error_detail,
)
from app.core.supabase_settings import SupabaseSettings, SupabaseSettingsError
from app.services.supabase_persistence import SupabasePersistenceError
from app.schemas.interview_chat import InterviewChatRequest, InterviewChatResponse
from app.schemas.coaching import (
    CoachingAnalyzeRequest,
    CoachingResponse,
    TerminalResponseReason,
)
from app.schemas.answer_revision import (
    AnswerRevisionCreateRequest,
    AnswerRevisionResponse,
)
from app.schemas.question_tts import CoachTtsRequest, QuestionTtsRequest, QuestionTtsResponse
from app.schemas.practice_setup import (
    CreatePracticeSessionRequest,
    JobPostingListResponse,
    JobPostingSummary,
    PracticeSessionResponse,
)
from app.schemas.alio_recruitment import (
    AlioRecruitmentSearchResponse,
    AlioRecruitmentAnalysisRequest,
    SaveAnalyzedAlioRecruitmentRequest,
)
from app.schemas.job_search_intent import (
    JobSearchIntentRequest,
    JobSearchIntentResponse,
)
from app.schemas.public_employment_recruitment import (
    PublicEmploymentRecruitmentAnalysisRequest,
    PublicEmploymentRecruitmentSearchResponse,
    SaveAnalyzedPublicEmploymentRecruitmentRequest,
)
from app.schemas.mofe_recruitment import (
    MofeRecruitmentAnalysisRequest,
    MofeRecruitmentSearchResponse,
    SaveAnalyzedMofeRecruitmentRequest,
)
from app.schemas.incheon_recruitment import IncheonRecruitmentSearchResponse
from app.schemas.ncs_competency import NcsBackendCompetenciesResponse
from app.schemas.github_readme import (
    GithubReadmeAnalysisRequest,
    GithubReadmeAnalysisResponse,
)
from app.schemas.resume import ResumeAnalysisResponse
from app.services.resume_analysis import (
    MAX_PDF_BYTES, ResumeAnalysisUnavailable, build_resume_analysis_service_from_env,
)
from app.schemas.saramin_recommendation import (
    ReviewRecommendedJobRequest,
    SaveReviewedPrivateJobRequest,
    SaraminRecommendationRequest,
    SaraminRecommendationResponse,
)
from app.services.saramin_recommendation import (
    SaraminRecommendationService,
    SaraminRecommendationUnavailable,
    build_saramin_recommendation_service_from_env,
)
from app.services.alio_recruitment import (
    AlioRecruitmentService,
    AlioRecruitmentSettings,
    AlioRecruitmentUnavailable,
    UnavailableAlioRecruitmentService,
)
from app.services.alio_requirement_analysis import (
    AlioRequirementAnalysisService,
    AlioRequirementAnalysisUnavailable,
    build_alio_requirement_analysis_service_from_env,
)
from app.services.public_employment_recruitment import (
    PublicEmploymentRecruitmentService,
    PublicEmploymentRecruitmentSettings,
    PublicEmploymentRecruitmentUnavailable,
    UnavailablePublicEmploymentRecruitmentService,
)
from app.services.mofe_recruitment import (
    MofeRecruitmentService,
    MofeRecruitmentSettings,
    MofeRecruitmentUnavailable,
    UnavailableMofeRecruitmentService,
)
from app.services.incheon_recruitment import (
    IncheonRecruitmentService,
    IncheonRecruitmentSettings,
    IncheonRecruitmentUnavailable,
    UnavailableIncheonRecruitmentService,
)
from app.services.job_search_intent import (
    JobSearchIntentService,
    JobSearchIntentUnavailable,
    build_job_search_intent_service_from_env,
    infer_job_search_intent,
)
from app.services.ncs_competency import (
    NcsCompetencyService,
    SupabaseNcsSnapshotStore,
    NcsCompetencySettings,
    NcsCompetencyUnavailable,
    UnavailableNcsCompetencyService,
)
from app.services.github_readme_analysis import (
    GithubReadmeAnalysisService,
    GithubReadmeAnalysisUnavailable,
    GithubReadmeNotFound,
    build_github_readme_analysis_service_from_env,
)
from app.services.coach_tts import CoachTtsUnavailableError, TtsWorkerClient
from app.services.coaching_context import (
    CoachingContextConflict,
    CoachingContextNotFound,
    build_demo_coaching_service,
)
from app.services.coaching_errors import (
    CoachingCreditsError,
    CoachingBudgetExceededError,
    CoachingProviderError,
    CoachingRateLimitError,
    CoachingTimeoutError,
)
from app.services.coaching_diagnostics import (
    CoachingDiagnostics, coaching_diagnostics_scope, record_coaching_failure, record_observation_failure,
)
from app.services.coaching_runtime import build_coaching_service_from_env
from app.services.interview_chat import InterviewChatConflict, build_interview_chat_service
from app.services.coaching_observability import (
    DEFAULT_PROMPT_VERSION,
    DEFAULT_SKILL_VERSION,
    CoachingObservation,
    CoachingObservationSink,
    activate_coaching_trace,
    active_coaching_trace,
    build_coaching_observation_sink_from_env,
    observation_identity,
    reset_coaching_trace,
    set_active_coaching_identity,
)
from app.services.delivery_analysis import DeliveryAnalyzer
from app.services.answer_revisions import AnswerRevisionService
from app.services.local_analysis_jobs import AudioValidationError, LocalAnalysisJobService
from app.services.persistent_analysis_jobs import AnalysisRequest, PersistentAnalysisJobService
from app.services.practice_history import PracticeHistoryService
from app.services.practice_setup import (
    PracticeSetupService,
    PracticeSetupUnavailable,
    UnavailablePracticeSetupService,
)
from app.services.question_rubric_generator import (
    OllamaQuestionRubricGenerator,
    QuestionRubricUnavailableError,
)
from app.services.preset_question_audio import (
    LocalPresetQuestionAudioRepository,
    PresetQuestionAudioService,
    PresetQuestionAudioUnavailable,
    SupabasePresetQuestionAudioRepository,
)
from app.services.question_tts import QuestionTtsInputError, QuestionTtsService, QuestionTtsUnavailableError, normalize_question
from app.services.question_tts_persistence import SupabaseQuestionTtsRepository
from app.services.question_tts_stream import (
    QuestionTtsStreamService,
    StreamAudio,
    StreamComplete,
    StreamError,
    StreamStart,
)
from app.services.stt_transcriber import FasterWhisperTranscriber
from app.services.supabase_persistence import SupabaseAnalysisRepository, SupabasePersistenceError
from app.services.supabase_answer_revisions import SupabaseAnswerRevisionRepository
from app.services.mcp_context_gateway import (
    McpContextGatewayError,
    begin_mcp_observation,
    observed_mcp_tool_names,
    reset_mcp_observation,
)
from app.services.supabase_coaching_context import CoachingContextPersistenceError
from app.services.supabase_coaching_runs import CoachingRunPersistenceError
from app.services.supabase_practice_setup import SupabasePracticeSetupRepository
from app.services.tts_asset_selector import TtsAssetSelector
from app.services.vad_detector import SileroVadDetector
from services.llm import OutputContractError, build_terminal_response
from mcp_server.server import create_http_mcp_server


class _UnavailableQuestionTtsService:
    def create(self, user: AuthenticatedUser, question: str) -> Any:
        raise QuestionTtsUnavailableError()

    def read(self, user: AuthenticatedUser, audio_id: str, now: datetime) -> bytes:
        raise QuestionTtsUnavailableError()


class _UnavailableQuestionTtsStreamService:
    def ensure_ready(self) -> None:
        raise QuestionTtsUnavailableError()

    def events(self, user: AuthenticatedUser, question: str, cancel: threading.Event) -> Iterator[object]:
        raise QuestionTtsUnavailableError()
        yield from ()


class _UnavailablePresetQuestionAudioService:
    def read_wav(self, question_id: str) -> bytes:
        raise PresetQuestionAudioUnavailable()


class _UnavailableAnswerRevisionService:
    def confirm(self, *args: Any, **kwargs: Any) -> AnswerRevisionResponse:
        raise SupabasePersistenceError(
            "CONFIGURATION_ERROR", "답변 revision 저장소가 설정되지 않았습니다."
        )


def _coaching_error_response(
    *,
    status_code: int,
    state: FailureState,
    code: str,
    message: str,
    retryable: bool,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ApiErrorResponse(
        detail=ApiErrorDetail(
            state=state,
            code=code,
            message=message,
            retryable=retryable,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=headers,
    )


def _set_coaching_observation_result(
    request: Request,
    result: CoachingResponse,
    model_name: str,
) -> None:
    request.state.coaching_model = model_name
    request.state.coaching_status = result.status.value
    request.state.coaching_criterion_count = len(result.criterion_assessments)
    request.state.coaching_gap_count = len(result.gaps)
    request.state.coaching_cost_usd = 0.0 if model_name.startswith("mock") else None


def _failure_state_for_status(status_code: int) -> FailureState | None:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return FailureState.AUTH_ERROR
    if status_code in {
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_502_BAD_GATEWAY,
    }:
        return FailureState.SCHEMA_VIOLATION
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return FailureState.RATE_LIMITED
    if status_code == status.HTTP_504_GATEWAY_TIMEOUT:
        return FailureState.TIMEOUT
    if status_code in {
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    }:
        return FailureState.CONTEXT_ERROR
    if status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return FailureState.PROVIDER_ERROR
    return None


def _record_coaching_observation(
    sink: CoachingObservationSink,
    request: Request,
    *,
    latency_ms: float,
    response_status: int,
) -> None:
    diagnostics = getattr(request.state, "coaching_diagnostics", None) or CoachingDiagnostics()
    if response_status >= 400 and diagnostics.failure_stage is None:
        record_coaching_failure("request", "COACHING_REQUEST_FAILED")
    trace_context = active_coaching_trace()
    explicit_cost = getattr(request.state, "coaching_cost_usd", None)
    try:
        sink.record(
            CoachingObservation(
                trace_id=(
                    trace_context.trace_id
                    if trace_context is not None
                    else getattr(request.state, "coaching_trace_id", None)
                )
                or uuid4().hex,
                **diagnostics.metadata(),
                user_key=getattr(request.state, "coaching_user_key", None),
                session_key=getattr(request.state, "coaching_session_key", None),
                model=getattr(request.state, "coaching_model", "not_started"),
                prompt_version=getattr(
                    request.state,
                    "coaching_prompt_version",
                    os.getenv("COACHING_PROMPT_VERSION", DEFAULT_PROMPT_VERSION),
                ),
                skill_version=getattr(
                    request.state,
                    "coaching_skill_version",
                    os.getenv("COACHING_SKILL_VERSION", DEFAULT_SKILL_VERSION),
                ),
                status=getattr(request.state, "coaching_status", None),
                latency_ms=latency_ms,
                input_tokens=(
                    trace_context.input_tokens
                    if trace_context is not None and trace_context.has_input_tokens
                    else None
                ),
                output_tokens=(
                    trace_context.output_tokens
                    if trace_context is not None and trace_context.has_output_tokens
                    else None
                ),
                cost_usd=(
                    explicit_cost
                    if explicit_cost is not None
                    else (
                        trace_context.cost_usd
                        if trace_context is not None and trace_context.has_cost
                        else None
                    )
                ),
                failure_state=getattr(
                    request.state,
                    "coaching_failure_state",
                    _failure_state_for_status(response_status),
                ),
                criterion_count=getattr(
                    request.state, "coaching_criterion_count", 0
                ),
                gap_count=getattr(request.state, "coaching_gap_count", 0),
            )
        )
    except Exception:
        # 관측 장애가 사용자 API의 성공·실패 의미를 바꾸지 않게 한다.
        record_observation_failure(diagnostics.trace_id)
        return


def cors_origins_from_env(environ: Mapping[str, str] | None = None) -> list[str]:
    source = os.environ if environ is None else environ
    raw = source.get("CORS_ALLOWED_ORIGINS", "")
    configured_origins = [value.strip() for value in raw.split(",") if value.strip()]
    local_origins = [
        "http://localhost:18080",
        "http://127.0.0.1:18080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    return configured_origins or local_origins


def _create_question_feedback_generator() -> OllamaQuestionRubricGenerator | None:
    enabled = os.getenv("LLM_FEEDBACK_ENABLED", "false").strip().lower()
    if enabled not in {"1", "true", "yes"}:
        return None
    try:
        return OllamaQuestionRubricGenerator()
    except (QuestionRubricUnavailableError, ValueError):
        return None


def _create_preset_question_audio_service() -> PresetQuestionAudioService | _UnavailablePresetQuestionAudioService:
    catalog_path = Path(__file__).resolve().parents[2] / "configs" / "tts" / "tts_template_catalog.json"
    local_audio_dir = os.getenv("PRESET_QUESTION_AUDIO_DIR", "").strip()
    if local_audio_dir:
        return PresetQuestionAudioService(
            TtsAssetSelector(catalog_path),
            LocalPresetQuestionAudioRepository(Path(local_audio_dir)),
        )
    try:
        settings = SupabaseSettings.from_env(require_service_role=True)
    except SupabaseSettingsError:
        return _UnavailablePresetQuestionAudioService()
    return PresetQuestionAudioService(
        TtsAssetSelector(catalog_path),
        SupabasePresetQuestionAudioRepository(settings),
    )


def create_app(
    service: LocalAnalysisJobService | PersistentAnalysisJobService | None = None,
    token_verifier: SupabaseJwtVerifier | Any | None = None,
    coaching_service: Any | None = None,
    interview_chat_service: Any | None = None,
    question_tts_service: QuestionTtsService | Any | None = None,
    question_tts_stream_service: QuestionTtsStreamService | Any | None = None,
    preset_question_audio_service: PresetQuestionAudioService | Any | None = None,
    practice_setup_service: PracticeSetupService | Any | None = None,
    alio_recruitment_service: AlioRecruitmentService | Any | None = None,
    public_employment_recruitment_service: PublicEmploymentRecruitmentService | Any | None = None,
    mofe_recruitment_service: MofeRecruitmentService | Any | None = None,
    incheon_recruitment_service: IncheonRecruitmentService | Any | None = None,
    ncs_competency_service: NcsCompetencyService | Any | None = None,
    github_readme_analysis_service: GithubReadmeAnalysisService | Any | None = None,
    saramin_recommendation_service: SaraminRecommendationService | Any | None = None,
    job_search_intent_service: JobSearchIntentService | Any | None = None,
    alio_requirement_analysis_service: AlioRequirementAnalysisService | Any | None = None,
    coaching_observation_sink: CoachingObservationSink | None = None,
    allowed_origins: list[str] | None = None,
    answer_revision_service: AnswerRevisionService | Any | None = None,
    resume_analysis_service: Any | None = None,
) -> FastAPI:
    http_mcp = create_http_mcp_server(token_verifier)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async with http_mcp.session_manager.run():
            if token_verifier is None:
                build_access_token_verifier_from_env()
            if question_tts_service is None and question_tts_stream_service is None:
                try:
                    if os.getenv("QUESTION_TTS_MODEL_PATH", "").strip():
                        from app.core.question_tts_settings import QuestionTtsSettings
                        from app.services.qwen_question_tts import QwenQuestionTtsSynthesizer

                        settings = QuestionTtsSettings.from_env()
                        synthesizer = QwenQuestionTtsSynthesizer.from_settings(settings)
                    else:
                        from app.services.remote_question_tts import (
                            RemoteQuestionTtsSynthesizer,
                        )

                        synthesizer = RemoteQuestionTtsSynthesizer()
                    synthesizer.warmup()
                    repository = SupabaseQuestionTtsRepository(SupabaseSettings.from_env())
                    application.state.question_tts_service = QuestionTtsService(
                        synthesizer,
                        repository,
                    )
                    application.state.question_tts_stream_service = QuestionTtsStreamService(synthesizer, repository)
                except Exception:
                    application.state.question_tts_service = _UnavailableQuestionTtsService()
                    application.state.question_tts_stream_service = _UnavailableQuestionTtsStreamService()
            _start_stt_warmup(application)
            yield

    app = FastAPI(
        title="말해봄 로컬 분석 API", version="0.1.0", lifespan=lifespan
    )
    app.state.coaching_observation_sink = (
        coaching_observation_sink or build_coaching_observation_sink_from_env()
    )

    @app.middleware("http")
    async def observe_coaching_request(request: Request, call_next):
        if request.url.path != "/api/agent":
            return await call_next(request)

        with coaching_diagnostics_scope() as diagnostics:
            request.state.coaching_diagnostics = diagnostics
            started = time.perf_counter()
            trace_context, trace_token = activate_coaching_trace(diagnostics.trace_id)
            mcp_observation_token = begin_mcp_observation()
            request.state.coaching_trace_id = trace_context.trace_id
            try:
                response = await call_next(request)
            except Exception:
                if diagnostics.failure_stage is None:
                    record_coaching_failure("internal", "COACHING_INTERNAL_ERROR")
                _record_coaching_observation(
                    app.state.coaching_observation_sink,
                    request,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    response_status=500,
                )
                record_request_link(app, request, trace_context.trace_id, 500,
                                    (time.perf_counter() - started) * 1000)
                return PlainTextResponse("Internal Server Error", status_code=500,
                    headers={"X-Trace-Id": trace_context.trace_id, "X-Request-Id": trace_context.trace_id})
            else:
                _record_coaching_observation(
                    app.state.coaching_observation_sink,
                    request,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    response_status=response.status_code,
                )
                response.headers["X-Trace-Id"] = trace_context.trace_id
                response.headers["X-Request-Id"] = trace_context.trace_id
                record_request_link(app, request, trace_context.trace_id, response.status_code,
                                    (time.perf_counter() - started) * 1000)
                tool_names = observed_mcp_tool_names()
                if tool_names:
                    response.headers["X-MCP-Tools"] = ",".join(tool_names)
                return response
            finally:
                reset_mcp_observation(mcp_observation_token)
                reset_coaching_trace(trace_token)

    @app.exception_handler(RequestValidationError)
    async def coaching_validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ):
        if request.url.path.startswith("/api/resume/assist/"):
            return JSONResponse(status_code=422, content={"detail": "이력서 요청 형식을 확인해 주세요."}, headers={"Cache-Control": "no-store"})
        if request.url.path != "/api/agent":
            return await request_validation_exception_handler(request, error)
        return _coaching_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            state=FailureState.SCHEMA_VIOLATION,
            code="REQUEST_SCHEMA_VIOLATION",
            message="코칭 요청 형식을 확인해 주세요.",
            retryable=False,
        )
    register_chat_request_tracing(app)
    install_loading_progress(app)
    cors_origins = allowed_origins if allowed_origins is not None else cors_origins_from_env()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=TRACE_HEADERS,
    )
    if service is not None:
        app.state.analysis_jobs = service
    else:
        try:
            settings = SupabaseSettings.from_env()
            app.state.analysis_jobs = PersistentAnalysisJobService(
                SupabaseAnalysisRepository(settings), FasterWhisperTranscriber(),
                vad_detector=SileroVadDetector(), delivery_analyzer=DeliveryAnalyzer(),
                question_feedback_generator=_create_question_feedback_generator(),
            )
        except SupabaseSettingsError:
            app.state.analysis_jobs = LocalAnalysisJobService(
                FasterWhisperTranscriber(), vad_detector=SileroVadDetector(), delivery_analyzer=DeliveryAnalyzer(),
            )
    app.state.question_tts_service = question_tts_service or _UnavailableQuestionTtsService()
    app.state.question_tts_stream_service = question_tts_stream_service or _UnavailableQuestionTtsStreamService()
    app.state.preset_question_audio_service = preset_question_audio_service or _create_preset_question_audio_service()
    if practice_setup_service is not None:
        app.state.practice_setup_service = practice_setup_service
    else:
        try:
            app.state.practice_setup_service = PracticeSetupService(
                SupabasePracticeSetupRepository(SupabaseSettings.from_env())
            )
        except SupabaseSettingsError:
            app.state.practice_setup_service = UnavailablePracticeSetupService()
    if alio_recruitment_service is not None:
        app.state.alio_recruitment_service = alio_recruitment_service
    else:
        try:
            app.state.alio_recruitment_service = AlioRecruitmentService(
                AlioRecruitmentSettings.from_env()
            )
        except AlioRecruitmentUnavailable as error:
            app.state.alio_recruitment_service = UnavailableAlioRecruitmentService(
                str(error)
            )
    if public_employment_recruitment_service is not None:
        app.state.public_employment_recruitment_service = (
            public_employment_recruitment_service
        )
    else:
        try:
            app.state.public_employment_recruitment_service = (
                PublicEmploymentRecruitmentService(
                    PublicEmploymentRecruitmentSettings.from_env()
                )
            )
        except PublicEmploymentRecruitmentUnavailable as error:
            app.state.public_employment_recruitment_service = (
                UnavailablePublicEmploymentRecruitmentService(str(error))
            )
    if mofe_recruitment_service is not None:
        app.state.mofe_recruitment_service = mofe_recruitment_service
    else:
        try:
            app.state.mofe_recruitment_service = MofeRecruitmentService(
                MofeRecruitmentSettings.from_env()
            )
        except MofeRecruitmentUnavailable as error:
            app.state.mofe_recruitment_service = UnavailableMofeRecruitmentService(
                str(error)
            )
    if incheon_recruitment_service is not None:
        app.state.incheon_recruitment_service = incheon_recruitment_service
    else:
        try:
            app.state.incheon_recruitment_service = IncheonRecruitmentService(
                IncheonRecruitmentSettings.from_env()
            )
        except IncheonRecruitmentUnavailable as error:
            app.state.incheon_recruitment_service = UnavailableIncheonRecruitmentService(
                str(error)
            )
    if ncs_competency_service is not None:
        app.state.ncs_competency_service = ncs_competency_service
    else:
        try:
            app.state.ncs_competency_service = NcsCompetencyService(
                NcsCompetencySettings.from_env(),
                snapshot_store=SupabaseNcsSnapshotStore(SupabaseSettings.from_env()),
            )
        except (NcsCompetencyUnavailable, SupabaseSettingsError) as error:
            app.state.ncs_competency_service = UnavailableNcsCompetencyService(
                str(error)
            )
    app.state.github_readme_analysis_service = (
        github_readme_analysis_service
        if github_readme_analysis_service is not None
        else build_github_readme_analysis_service_from_env()
    )
    app.state.resume_analysis_service = (
        resume_analysis_service if resume_analysis_service is not None
        else build_resume_analysis_service_from_env()
    )
    app.state.saramin_recommendation_service = (
        saramin_recommendation_service
        if saramin_recommendation_service is not None
        else build_saramin_recommendation_service_from_env()
    )
    app.state.alio_requirement_analysis_service = (
        alio_requirement_analysis_service
        if alio_requirement_analysis_service is not None
        else build_alio_requirement_analysis_service_from_env()
    )
    app.state.job_search_intent_service = (
        job_search_intent_service
        if job_search_intent_service is not None
        else build_job_search_intent_service_from_env()
    )
    if answer_revision_service is not None:
        app.state.answer_revision_service = answer_revision_service
    else:
        try:
            app.state.answer_revision_service = AnswerRevisionService(
                SupabaseAnswerRevisionRepository(SupabaseSettings.from_env())
            )
        except SupabaseSettingsError:
            app.state.answer_revision_service = _UnavailableAnswerRevisionService()
    app.state.coaching_service = (
        coaching_service
        if coaching_service is not None
        else build_coaching_service_from_env(app.state.coaching_observation_sink)
    )
    app.state.interview_chat_service = (
        interview_chat_service if interview_chat_service is not None
        else build_interview_chat_service(app.state.coaching_service, app.state.analysis_jobs)
    )
    require_authenticated_user = create_require_authenticated_user(token_verifier)
    from app.services.transcript_normalization import install_transcript_normalization
    install_transcript_normalization(app, require_authenticated_user)
    from app.routers.preparation_conversation import register_preparation_routes
    register_preparation_routes(app, require_authenticated_user)
    from app.services.resume_assistance_routes import register_resume_assistance_routes
    register_resume_assistance_routes(app, require_authenticated_user)

    @app.post("/api/agent/chat", response_model=InterviewChatResponse)
    def interview_chat(
        request: InterviewChatRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> InterviewChatResponse:
        active_service = app.state.interview_chat_service
        if active_service is None:
            raise HTTPException(status_code=503, detail="면접 대화 서비스를 실행할 설정이 필요합니다.")
        started = time.perf_counter()
        outcome = "error"
        try:
            result = active_service.respond(user, request)
            outcome = result.status
            return result
        except KeyError:
            raise HTTPException(status_code=404, detail="대화 또는 유효한 연습 기록을 찾을 수 없습니다. 비교 결과에서 다시 시작해 주세요.") from None
        except InterviewChatConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        except CoachingCreditsError:
            raise HTTPException(status_code=402, detail="모델 크레딧 또는 키 사용 한도를 확인해 주세요.") from None
        except CoachingRateLimitError as error:
            headers = {"Retry-After": str(error.retry_after_seconds)} if error.retry_after_seconds else None
            raise HTTPException(status_code=429, detail="요청이 많아 잠시 뒤 다시 시도해 주세요.", headers=headers) from None
        except CoachingTimeoutError:
            raise HTTPException(status_code=504, detail="면접 대화 응답 시간이 초과되었습니다. 다시 시도해 주세요.") from None
        except OutputContractError:
            raise HTTPException(status_code=502, detail="면접 대화 응답 형식을 확인하지 못했습니다. 다시 시도해 주세요.") from None
        except SupabasePersistenceError:
            raise HTTPException(status_code=503, detail="면접 대화 기록을 저장하거나 불러오지 못했습니다. 다시 시도해 주세요.") from None
        except CoachingProviderError:
            raise HTTPException(status_code=503, detail="면접 대화 문맥 또는 모델에 연결하지 못했습니다. 다시 시도해 주세요.") from None
        finally:
            try:
                app.state.coaching_observation_sink.record(CoachingObservation(
                    trace_name="interview.chat", trace_id=active_coaching_trace().trace_id, user_key=observation_identity(user.user_id),
                    session_key=observation_identity(str(request.practice_session_id)),
                    model=active_service.provider.model_name,
                    prompt_version="interview-conversation-v1", skill_version="interview-conversation-v2",
                    status=outcome, latency_ms=(time.perf_counter() - started) * 1000,
                ))
            except Exception:
                pass

    @app.post(
        "/api/agent",
        response_model=CoachingResponse,
        responses={
            401: {"model": ApiErrorResponse},
            404: {"model": ApiErrorResponse},
            409: {"model": ApiErrorResponse},
            422: {"model": ApiErrorResponse},
            429: {"model": ApiErrorResponse},
            502: {"model": ApiErrorResponse},
            503: {"model": ApiErrorResponse},
            504: {"model": ApiErrorResponse},
        },
    )
    def analyze_coaching(
        request: CoachingAnalyzeRequest,
        http_request: Request,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> CoachingResponse | Response:
        http_request.state.coaching_user_key = observation_identity(user.user_id)
        http_request.state.coaching_session_key = observation_identity(
            str(request.answer_revision_id)
        )
        set_active_coaching_identity(
            user_key=http_request.state.coaching_user_key,
            session_key=http_request.state.coaching_session_key,
        )
        active_service = app.state.coaching_service
        if active_service is None:
            mock_enabled = os.getenv("COACHING_MOCK_ENABLED", "false").strip().lower()
            if mock_enabled not in {"1", "true", "yes"}:
                result = build_terminal_response(
                    TerminalResponseReason(
                        status="unavailable",
                        reason="운영 코칭 공급자 또는 MCP·Supabase 설정이 필요합니다.",
                    )
                )
                _set_coaching_observation_result(http_request, result, "unavailable")
                return result
            active_service = build_demo_coaching_service(user.user_id)
            http_request.state.coaching_model = "mock-v1"
        http_request.state.coaching_model = getattr(
            active_service, "model_name",
            getattr(http_request.state, "coaching_model", "configured-provider"),
        )
        try:
            http_request.state.coaching_prompt_version = getattr(
                active_service,
                "prompt_version",
                os.getenv("COACHING_PROMPT_VERSION", DEFAULT_PROMPT_VERSION),
            )
            http_request.state.coaching_skill_version = getattr(
                active_service,
                "skill_version",
                os.getenv("COACHING_SKILL_VERSION", DEFAULT_SKILL_VERSION),
            )
            result = active_service.analyze(user, request)
            _set_coaching_observation_result(
                http_request,
                result,
                getattr(
                    active_service,
                    "model_name",
                    getattr(
                        http_request.state,
                        "coaching_model",
                        "configured-provider",
                    ),
                ),
            )
            return result
        except CoachingContextNotFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=api_error_detail(
                    state=FailureState.CONTEXT_ERROR,
                    code="COACHING_CONTEXT_NOT_FOUND",
                    message="사용할 수 있는 코칭 문맥을 찾지 못했습니다.",
                    retryable=False,
                ),
            ) from None
        except CoachingContextConflict as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=api_error_detail(
                    state=FailureState.CONTEXT_ERROR,
                    code="COACHING_CONTEXT_CONFLICT",
                    message=str(error),
                    retryable=False,
                ),
            ) from error
        except OutputContractError:
            return _coaching_error_response(
                status_code=status.HTTP_502_BAD_GATEWAY,
                state=FailureState.SCHEMA_VIOLATION,
                code="COACHING_OUTPUT_SCHEMA_VIOLATION",
                message="코칭 결과를 검증하지 못했습니다. 다시 시도해 주세요.",
                retryable=True,
            )
        except CoachingTimeoutError:
            return _coaching_error_response(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                state=FailureState.TIMEOUT,
                code="COACHING_TIMEOUT",
                message="코칭 응답 시간이 초과되었습니다. 다시 시도해 주세요.",
                retryable=True,
            )
        except CoachingRateLimitError as error:
            headers = (
                {"Retry-After": str(error.retry_after_seconds)}
                if error.retry_after_seconds is not None
                else None
            )
            return _coaching_error_response(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                state=FailureState.RATE_LIMITED,
                code="COACHING_RATE_LIMITED",
                message="요청이 많아 잠시 뒤 다시 시도해 주세요.",
                retryable=True,
                headers=headers,
            )
        except CoachingBudgetExceededError:
            return _coaching_error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                state=FailureState.PROVIDER_ERROR,
                code="COACHING_BUDGET_EXCEEDED",
                message="이번 코칭 요청의 모델 비용 상한을 초과했습니다.",
                retryable=False,
            )
        except McpContextGatewayError as error:
            http_request.state.coaching_failure_state = FailureState.MCP_ERROR
            record_coaching_failure("context", "COACHING_CONTEXT_LOAD_FAILED")
            return _coaching_error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                state=FailureState.MCP_ERROR,
                code=error.code,
                message="코칭 문맥에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
                retryable=error.retryable,
            )
        except (
            CoachingProviderError,
            CoachingContextPersistenceError,
            CoachingRunPersistenceError,
        ):
            return _coaching_error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                state=FailureState.PROVIDER_ERROR,
                code="COACHING_PROVIDER_UNAVAILABLE",
                message="코칭 문맥 또는 모델에 연결하지 못했습니다. 다시 시도해 주세요.",
                retryable=True,
            )

    @app.get("/api/preset-questions/{question_id}/audio")
    def get_preset_question_audio(question_id: str) -> Response:
        try:
            content = app.state.preset_question_audio_service.read_wav(question_id)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="질문 음성을 찾을 수 없습니다.") from None
        except PresetQuestionAudioUnavailable:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="질문 음성을 준비하지 못했습니다. 다시 시도해 주세요.",
            ) from None
        return Response(
            content=content,
            media_type="audio/wav",
            headers={"Cache-Control": "public, max-age=300"},
        )

    @app.post("/api/questions/tts", response_model=QuestionTtsResponse)
    def create_question_tts(
        request: QuestionTtsRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> QuestionTtsResponse:
        try:
            created = app.state.question_tts_service.create(user, request.question)
        except QuestionTtsInputError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.message) from error
        except QuestionTtsUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="질문 음성을 만들지 못했습니다. 다시 시도해 주세요.",
            ) from None
        return QuestionTtsResponse(
            audioUrl=f"/api/audio/questions/{created.record.audio_id}",
            text=created.text,
            durationMs=created.record.duration_ms,
            expiresAt=created.record.expires_at,
        )

    @app.post("/api/coach-tts")
    def create_coach_tts(
        request: CoachTtsRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> Response:
        del user
        try:
            audio = TtsWorkerClient().synthesize(request.text)
        except CoachTtsUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="말하기 예시 음성을 만들지 못했습니다. 다시 시도해 주세요.",
            ) from None
        return Response(content=audio, media_type="audio/wav")

    @app.get("/api/coach-tts/health")
    def get_coach_tts_health(
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> dict[str, str]:
        del user
        if not TtsWorkerClient().is_ready():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="음성 엔진을 준비하고 있습니다.",
            )
        return {"status": "ready"}

    @app.post("/api/coach-tts/stream")
    def stream_coach_tts(
        request: CoachTtsRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> StreamingResponse:
        del user
        try:
            stream = TtsWorkerClient().synthesize_stream(request.text)
        except CoachTtsUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="말하기 예시 음성을 만들지 못했습니다. 다시 시도해 주세요.",
            ) from None
        return StreamingResponse(
            stream,
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/coach-tts/pcm-stream")
    async def stream_coach_tts_pcm(
        request: QuestionTtsRequest,
        http_request: Request,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> StreamingResponse:
        del user
        try:
            stream = TtsWorkerClient().synthesize_pcm_stream(request.question)
        except CoachTtsUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="말하기 예시 음성을 만들지 못했습니다. 다시 시도해 주세요.",
            ) from None

        async def event_iterator() -> AsyncIterator[bytes]:
            try:
                while not await http_request.is_disconnected():
                    chunk = await asyncio.to_thread(_next_stream_chunk, stream)
                    if chunk is None or await http_request.is_disconnected():
                        return
                    yield chunk
            finally:
                close = getattr(stream, "close", None)
                if callable(close):
                    close()

        return StreamingResponse(
            event_iterator(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/questions/tts/stream")
    def stream_question_tts(
        request: QuestionTtsRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> StreamingResponse:
        try:
            normalized_question = normalize_question(request.question)
            ensure_ready = getattr(app.state.question_tts_stream_service, "ensure_ready", None)
            if callable(ensure_ready):
                ensure_ready()
        except QuestionTtsInputError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.message) from error
        except QuestionTtsUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="질문 음성을 만들지 못했습니다. 다시 시도해 주세요.",
            ) from None

        cancel = threading.Event()

        def event_iterator() -> Iterator[bytes]:
            try:
                for event in app.state.question_tts_stream_service.events(user, normalized_question, cancel):
                    yield _encode_question_tts_stream_event(event)
            finally:
                cancel.set()

        return StreamingResponse(
            event_iterator(),
            media_type="application/x-ndjson",
            headers={"Content-Type": "application/x-ndjson; charset=utf-8"},
        )

    @app.get("/api/audio/questions/{audio_id}")
    def get_question_tts_audio(
        audio_id: str,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> Response:
        try:
            content = app.state.question_tts_service.read(user, audio_id, datetime.now(UTC))
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="질문 음성을 찾을 수 없습니다.") from None
        except QuestionTtsUnavailableError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="질문 음성을 읽지 못했습니다. 다시 시도해 주세요.",
            ) from None
        return Response(content=content, media_type="audio/wav")

    @app.get("/api/job-postings", response_model=JobPostingListResponse)
    def list_job_postings(
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> JobPostingListResponse:
        try:
            return app.state.practice_setup_service.list_job_postings(user)
        except (PracticeSetupUnavailable, SupabasePersistenceError) as error:
            message = getattr(error, "message", str(error))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=message,
            ) from error

    @app.get(
        "/api/ncs/backend-competencies",
        response_model=NcsBackendCompetenciesResponse,
    )
    def get_ncs_backend_competencies(
        user: AuthenticatedUser = Depends(require_authenticated_user),
        source: Literal["api", "database"] = "api",
    ) -> NcsBackendCompetenciesResponse:
        try:
            if source == "database":
                return app.state.ncs_competency_service.stored_backend_competencies()
            return app.state.ncs_competency_service.backend_competencies()
        except NcsCompetencyUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.post("/api/resume/analyze", response_model=ResumeAnalysisResponse)
    async def analyze_resume_pdf(
        file: UploadFile = File(...),
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> ResumeAnalysisResponse:
        try:
            if not (file.filename or "").lower().endswith(".pdf"):
                raise ValueError("PDF 파일을 제출해 주세요.")
            data = await file.read(MAX_PDF_BYTES + 1)
            return await asyncio.to_thread(app.state.resume_analysis_service.analyze, data)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from None
        except ResumeAnalysisUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from None
        finally:
            await file.close()

    @app.post(
        "/api/github/readme/analyze",
        response_model=GithubReadmeAnalysisResponse,
    )
    def analyze_github_readme(
        request: GithubReadmeAnalysisRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> GithubReadmeAnalysisResponse:
        try:
            return app.state.github_readme_analysis_service.analyze(request)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        except GithubReadmeNotFound as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except GithubReadmeAnalysisUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.get("/api/agent/preparation/{conversation_id}/confirmed")
    def confirmed_preparation_experience(
        conversation_id: UUID,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ):
        active = app.state.preparation_conversation_service
        if active is None:
            raise HTTPException(status_code=503, detail="확인한 경험을 불러올 수 없습니다.")
        try:
            row = active.repository.load(user, conversation_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="준비 대화를 찾을 수 없습니다.") from None
        except SupabasePersistenceError:
            raise HTTPException(status_code=503, detail="확인한 경험을 불러오지 못했습니다.") from None
        from app.services.preparation_conversation_repository import confirmed_context
        return {"experiences": [{"id": item["draft_id"], "facts": item["facts"],
            "source_type": "user_chat", "user_confirmed": True}
            for item in confirmed_context([row])]}

    @app.post(
        "/api/job-search/recommendations",
        response_model=SaraminRecommendationResponse,
    )
    def recommend_saramin_jobs(
        request: SaraminRecommendationRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> SaraminRecommendationResponse:
        try:
            if request.preparation_conversation_id is None:
                return app.state.saramin_recommendation_service.recommend(request)
            active = app.state.preparation_conversation_service
            if active is None:
                raise HTTPException(status_code=503, detail="저장한 경험을 불러올 수 없습니다. 다시 시도해 주세요.")
            try:
                row = active.repository.load(user, request.preparation_conversation_id)
            except KeyError:
                raise HTTPException(status_code=404, detail="준비 대화를 찾을 수 없습니다.") from None
            except SupabasePersistenceError:
                raise HTTPException(status_code=503, detail="저장한 경험을 불러오지 못했습니다. 다시 시도해 주세요.") from None
            from app.services.preparation_conversation_repository import confirmed_context
            return app.state.saramin_recommendation_service.recommend(
                request, confirmed_experience=confirmed_context([row]))
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        except GithubReadmeNotFound as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except GithubReadmeAnalysisUnavailable as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except SaraminRecommendationUnavailable as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    @app.post(
        "/api/job-search/recommendations/analyze",
        response_model=JobPostingSummary,
        status_code=status.HTTP_201_CREATED,
    )
    def analyze_recommended_job(
        request: ReviewRecommendedJobRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> JobPostingSummary:
        try:
            verified = app.state.saramin_recommendation_service.verify_for_review(
                request.source_url
            )
            existing = app.state.practice_setup_service.list_job_postings(user)
            for posting in existing.job_postings:
                if posting.data_origin == "private_job" and posting.source_url == verified.source_url:
                    return posting
            requirements = app.state.alio_requirement_analysis_service.analyze(
                AlioRecruitmentAnalysisRequest(
                    announcement_id=int(verified.posting_id),
                    company=verified.company,
                    title=verified.title,
                    source_url=verified.source_url,
                ),
                source_text=verified.details,
            )
            return app.state.practice_setup_service.save_reviewed_private_job(
                user,
                SaveReviewedPrivateJobRequest(
                    source=verified.source,
                    posting_id=verified.posting_id,
                    company=verified.company,
                    title=verified.title,
                    source_url=verified.source_url,
                    requirements=requirements,
                ),
            )
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        except SaraminRecommendationUnavailable as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except AlioRequirementAnalysisUnavailable as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
        except SupabasePersistenceError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error.message) from error
        except PracticeSetupUnavailable as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    @app.get(
        "/api/alio/recruitments",
        response_model=AlioRecruitmentSearchResponse,
    )
    def search_alio_recruitments(
        query: str,
        page: int = 1,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> AlioRecruitmentSearchResponse:
        normalized_query = query.strip()
        if not normalized_query or len(normalized_query) > 80 or not 1 <= page <= 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="검색어는 1~80자이며 페이지는 1~100 사이여야 합니다.",
            )
        try:
            return app.state.alio_recruitment_service.search(
                query=normalized_query,
                page=page,
                page_size=10,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        except AlioRecruitmentUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.post(
        "/api/job-search-intent",
        response_model=JobSearchIntentResponse,
    )
    def interpret_job_search_intent(
        request: JobSearchIntentRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> JobSearchIntentResponse:
        try:
            return app.state.job_search_intent_service.classify(request)
        except JobSearchIntentUnavailable:
            return infer_job_search_intent(request.message)

    @app.post(
        "/api/alio/recruitments/analyze",
        response_model=JobPostingSummary,
        status_code=status.HTTP_201_CREATED,
    )
    def analyze_alio_recruitment(
        request: AlioRecruitmentAnalysisRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> JobPostingSummary:
        try:
            source_text = app.state.alio_recruitment_service.get_analysis_source(
                announcement_id=request.announcement_id,
                title=request.title,
            )
            requirements = app.state.alio_requirement_analysis_service.analyze(
                request, source_text=source_text
            )
            return app.state.practice_setup_service.save_analyzed_alio_recruitment(
                user,
                SaveAnalyzedAlioRecruitmentRequest(
                    **request.model_dump(),
                    requirements=requirements,
                ),
            )
        except (AlioRequirementAnalysisUnavailable, AlioRecruitmentUnavailable) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        except SupabasePersistenceError as error:
            status_code = (
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if error.code == "INVALID_PRACTICE_SETUP"
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )
            raise HTTPException(status_code=status_code, detail=error.message) from error
        except PracticeSetupUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.get(
        "/api/public-employment/recruitments",
        response_model=PublicEmploymentRecruitmentSearchResponse,
    )
    def search_public_employment_recruitments(
        query: str,
        page: int = 1,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> PublicEmploymentRecruitmentSearchResponse:
        normalized_query = query.strip()
        if not normalized_query or len(normalized_query) > 80 or not 1 <= page <= 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="검색어는 1~80자이며 페이지는 1~100 사이여야 합니다.",
            )
        try:
            return app.state.public_employment_recruitment_service.search(
                query=normalized_query,
                page=page,
                page_size=10,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        except PublicEmploymentRecruitmentUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.post(
        "/api/public-employment/recruitments/analyze",
        response_model=JobPostingSummary,
        status_code=status.HTTP_201_CREATED,
    )
    def analyze_public_employment_recruitment(
        request: PublicEmploymentRecruitmentAnalysisRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> JobPostingSummary:
        try:
            source_text, source_url = (
                app.state.public_employment_recruitment_service.get_analysis_source(
                    announcement_id=request.announcement_id
                )
            )
            requirements = app.state.alio_requirement_analysis_service.analyze(
                AlioRecruitmentAnalysisRequest(
                    announcement_id=request.announcement_id,
                    company=request.company,
                    title=request.title,
                    source_url=source_url,
                ),
                source_text=source_text,
            )
            return app.state.practice_setup_service.save_analyzed_public_employment_recruitment(
                user,
                SaveAnalyzedPublicEmploymentRecruitmentRequest(
                    **request.model_dump(),
                    source_url=source_url,
                    requirements=requirements,
                ),
            )
        except (AlioRequirementAnalysisUnavailable, PublicEmploymentRecruitmentUnavailable) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        except SupabasePersistenceError as error:
            status_code = (
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if error.code == "INVALID_PRACTICE_SETUP"
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )
            raise HTTPException(status_code=status_code, detail=error.message) from error
        except PracticeSetupUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.get(
        "/api/mofe/recruitments",
        response_model=MofeRecruitmentSearchResponse,
    )
    def search_mofe_recruitments(
        query: str,
        page: int = 1,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> MofeRecruitmentSearchResponse:
        normalized_query = query.strip()
        if not normalized_query or len(normalized_query) > 80 or not 1 <= page <= 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="검색어는 1~80자이며 페이지는 1~100 사이여야 합니다.",
            )
        try:
            return app.state.mofe_recruitment_service.search(
                query=normalized_query,
                page=page,
                page_size=10,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        except MofeRecruitmentUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.get(
        "/api/incheon/recruitments",
        response_model=IncheonRecruitmentSearchResponse,
    )
    def search_incheon_recruitments(
        query: str,
        page: int = 1,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> IncheonRecruitmentSearchResponse:
        normalized_query = query.strip()
        if not normalized_query or len(normalized_query) > 80 or not 1 <= page <= 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="검색어는 1~80자이며 페이지는 1~100 사이여야 합니다.",
            )
        try:
            return app.state.incheon_recruitment_service.search(
                query=normalized_query,
                page=page,
                page_size=10,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        except IncheonRecruitmentUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.post(
        "/api/mofe/recruitments/analyze",
        response_model=JobPostingSummary,
        status_code=status.HTTP_201_CREATED,
    )
    def analyze_mofe_recruitment(
        request: MofeRecruitmentAnalysisRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> JobPostingSummary:
        try:
            source_text, source_url = app.state.mofe_recruitment_service.get_analysis_source(
                announcement_id=request.announcement_id
            )
            requirements = app.state.alio_requirement_analysis_service.analyze(
                AlioRecruitmentAnalysisRequest(
                    announcement_id=request.announcement_id,
                    company=request.company,
                    title=request.title,
                    source_url=source_url,
                ),
                source_text=source_text,
            )
            return app.state.practice_setup_service.save_analyzed_mofe_recruitment(
                user,
                SaveAnalyzedMofeRecruitmentRequest(
                    **request.model_dump(),
                    source_url=source_url,
                    requirements=requirements,
                ),
            )
        except (AlioRequirementAnalysisUnavailable, MofeRecruitmentUnavailable) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        except SupabasePersistenceError as error:
            status_code = (
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if error.code == "INVALID_PRACTICE_SETUP"
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )
            raise HTTPException(status_code=status_code, detail=error.message) from error
        except PracticeSetupUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.post(
        "/api/practice-sessions",
        response_model=PracticeSessionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_practice_session(
        request: CreatePracticeSessionRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> PracticeSessionResponse:
        try:
            return app.state.practice_setup_service.create_practice_session(
                user, request
            )
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="선택한 공고 또는 요구사항을 찾지 못했습니다.",
            ) from error
        except SupabasePersistenceError as error:
            status_code = (
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if error.code == "INVALID_PRACTICE_SETUP"
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )
            raise HTTPException(status_code=status_code, detail=error.message) from error
        except PracticeSetupUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

    @app.post("/analysis-jobs", status_code=status.HTTP_202_ACCEPTED)
    async def create_analysis_job(
        background_tasks: BackgroundTasks,
        source_id: str = Form(...),
        question_type: str = Form(...),
        attempt_no: int = Form(...),
        question_id: str | None = Form(None),
        custom_question_text: str | None = Form(None),
        practice_session_id: str | None = Form(None),
        audio: UploadFile = File(...),
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> dict[str, object]:
        try:
            content = await audio.read()
            if not isinstance(app.state.analysis_jobs, PersistentAnalysisJobService):
                job = app.state.analysis_jobs.create_job(source_id=source_id, filename=audio.filename or "upload", content=content, user_id=user.user_id)
                background_tasks.add_task(app.state.analysis_jobs.process, job.job_id)
                return job.to_dict()
            job = app.state.analysis_jobs.create_job(
                user, AnalysisRequest(source_id, question_type, attempt_no, question_id, custom_question_text, practice_session_id),
                audio.filename or "upload", content, audio.content_type,
            )
        except (AudioValidationError, SupabasePersistenceError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": error.code, "message": error.message},
            ) from error
        finally:
            await audio.close()

        background_tasks.add_task(app.state.analysis_jobs.process, str(job["job_id"]), user)
        return job

    @app.get("/analysis-jobs/{job_id}")
    def get_analysis_job(
        job_id: str, user: AuthenticatedUser = Depends(require_authenticated_user)
    ) -> dict[str, object]:
        try:
            if isinstance(app.state.analysis_jobs, PersistentAnalysisJobService):
                return app.state.analysis_jobs.get(job_id, user)
            return app.state.analysis_jobs.get(job_id, user_id=user.user_id).to_dict()
        except (KeyError, SupabasePersistenceError) as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 작업을 찾을 수 없습니다.") from error

    @app.post(
        "/analysis-jobs/{job_id}/answer-revisions",
        response_model=AnswerRevisionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def confirm_answer_revision(
        job_id: UUID,
        request: AnswerRevisionCreateRequest,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> AnswerRevisionResponse:
        try:
            return app.state.answer_revision_service.confirm(user, job_id, request)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="확정된 답변을 찾지 못했습니다.",
            ) from error
        except SupabasePersistenceError as error:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY if (
                error.code == "INVALID_ANSWER_REVISION"
            ) else status.HTTP_503_SERVICE_UNAVAILABLE
            message = getattr(error, "message", "답변 revision을 만들지 못했습니다.")
            raise HTTPException(status_code=status_code, detail=message) from error

    @app.delete("/analysis-jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_analysis_job(job_id: str, user: AuthenticatedUser = Depends(require_authenticated_user)) -> Response:
        if not isinstance(app.state.analysis_jobs, PersistentAnalysisJobService):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 작업을 찾을 수 없습니다.")
        try:
            app.state.analysis_jobs.delete(job_id, user)
        except (KeyError, SupabasePersistenceError) as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="분석 작업을 찾을 수 없습니다.") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def practice_history() -> PracticeHistoryService:
        if not isinstance(app.state.analysis_jobs, PersistentAnalysisJobService):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="연습 기록을 찾을 수 없습니다.")
        return PracticeHistoryService(app.state.analysis_jobs.repository)

    @app.get("/practice-records")
    def list_practice_records(user: AuthenticatedUser = Depends(require_authenticated_user)) -> dict[str, object]:
        try:
            return practice_history().list_records(user)
        except SupabasePersistenceError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error.message) from error

    @app.get("/practice-records/{practice_session_id}")
    def get_practice_record(
        practice_session_id: str,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> dict[str, object]:
        try:
            return practice_history().get_record(user, practice_session_id)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="연습 기록을 찾을 수 없습니다.") from None
        except SupabasePersistenceError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error.message) from error

    @app.delete("/practice-records/{practice_session_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_practice_record(
        practice_session_id: str,
        user: AuthenticatedUser = Depends(require_authenticated_user),
    ) -> Response:
        try:
            practice_history().delete_record(user, practice_session_id)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="연습 기록을 찾을 수 없습니다.") from None
        except SupabasePersistenceError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error.message) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.delete("/practice-records", status_code=status.HTTP_204_NO_CONTENT)
    def delete_all_practice_records(user: AuthenticatedUser = Depends(require_authenticated_user)) -> Response:
        try:
            practice_history().delete_all_records(user)
        except SupabasePersistenceError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error.message) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        """추론을 실행하지 않는 배포 health check."""

        return {"status": "ok"}

    app.state.http_mcp = http_mcp
    app.mount("/", http_mcp.streamable_http_app(), name="mcp-http")
    return app


def _start_stt_warmup(application: FastAPI) -> None:
    if os.getenv("STT_WARMUP_ENABLED", "true").strip().lower() in {"0", "false", "no", "off"}:
        return
    analysis_jobs = getattr(application.state, "analysis_jobs", None)
    transcriber = getattr(analysis_jobs, "transcriber", None)
    if not isinstance(transcriber, FasterWhisperTranscriber):
        return

    def warmup() -> None:
        try:
            transcriber.warmup()
        except Exception:
            # 모델 준비 실패는 분석 요청 시 기존 오류 처리로 안내한다.
            return

    threading.Thread(target=warmup, name="stt-model-warmup", daemon=True).start()


app = create_app()


def _next_stream_chunk(stream: Iterator[bytes]) -> bytes | None:
    try:
        return next(stream)
    except StopIteration:
        return None


def _encode_question_tts_stream_event(event: object) -> bytes:
    if isinstance(event, StreamStart):
        payload: dict[str, object] = {
            "type": "start",
            "text": event.text,
            "format": event.format,
            "sampleRate": event.sample_rate,
            "channels": event.channels,
        }
    elif isinstance(event, StreamAudio):
        payload = {
            "type": "audio",
            "sequence": event.sequence,
            "pcmBase64": base64.b64encode(event.pcm16).decode("ascii"),
        }
    elif isinstance(event, StreamComplete):
        payload = {
            "type": "complete",
            "audioUrl": f"/api/audio/questions/{event.record.audio_id}",
            "durationMs": event.record.duration_ms,
            "expiresAt": event.record.expires_at.isoformat(),
        }
    elif isinstance(event, StreamError):
        payload = {"type": "error", "code": event.code, "message": event.message}
    else:
        raise RuntimeError("Unknown question TTS stream event")
    return (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
