from __future__ import annotations

import logging
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

from app.core.auth import AuthenticatedUser
from app.schemas.delivery import DeliveryAnalysisResult
from app.schemas.stt import SttResult
from app.services.delivery_analysis import DeliveryAnalyzer
from app.services.local_analysis_jobs import AudioValidationError, MAX_AUDIO_BYTES, MAX_AUDIO_DURATION_SEC, MIN_AUDIO_DURATION_SEC, Transcriber
from app.services.question_rubric_generator import (
    QuestionFeedbackInputError,
    QuestionFeedbackUnavailableError,
    QuestionRubricInputError,
    QuestionRubricUnavailableError,
)
from app.services.stt_prompt_hints import build_stt_prompt_hints
from app.services.stt_transcriber import SUPPORTED_AUDIO_SUFFIXES
from app.services.supabase_persistence import SupabaseAnalysisRepository, SupabasePersistenceError
from app.services.vad_detector import SileroVadDetector, SpeechSegmentDetector

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisRequest:
    source_id: str
    question_type: str
    attempt_no: int
    question_id: str | None
    custom_question_text: str | None
    practice_session_id: str | None


@dataclass
class PendingAudio:
    path: Path
    source_id: str
    practice_session_id: str
    attempt_no: int
    question_type: str
    question_id: str | None
    custom_question_text: str | None


class PersistentAnalysisJobService:
    def __init__(self, repository: SupabaseAnalysisRepository, transcriber: Transcriber, working_dir: Path | str | None = None, vad_detector: SpeechSegmentDetector | None = None, delivery_analyzer: DeliveryAnalyzer | None = None, question_feedback_generator: object | None = None) -> None:
        self.repository = repository
        self.transcriber = transcriber
        self.vad_detector = vad_detector or SileroVadDetector()
        self.delivery_analyzer = delivery_analyzer or DeliveryAnalyzer()
        self.question_feedback_generator = question_feedback_generator
        self.working_dir = Path(working_dir or "local-analysis")
        self._pending: dict[str, PendingAudio] = {}
        self._progress: dict[str, dict[str, object]] = {}
        self._lock = Lock()

    def create_job(self, user: AuthenticatedUser, request: AnalysisRequest, filename: str, content: bytes, content_type: str | None) -> dict[str, object]:
        metadata = self._validated_metadata(user, request)
        path = self._write_validated_audio(filename, content)
        job_id = str(uuid4())
        try:
            row = self.repository.create_job(user, job_id, metadata, content, filename, content_type)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        with self._lock:
            self._pending[job_id] = PendingAudio(
                path=path,
                source_id=request.source_id.strip(),
                practice_session_id=str(metadata["practice_session_id"]),
                attempt_no=int(metadata["attempt_no"]),
                question_type=request.question_type,
                question_id=request.question_id,
                custom_question_text=request.custom_question_text,
            )
        self._set_progress(job_id, "분석 대기 중", 5)
        return _to_api_job(row)

    def process(self, job_id: str, user: AuthenticatedUser) -> None:
        with self._lock:
            pending = self._pending.get(job_id)
        if pending is None:
            return
        process_started = time.perf_counter()
        stage_ms: dict[str, float] = {}
        try:
            stage_started = time.perf_counter()
            self.repository.mark_processing(user, job_id)
            stage_ms["mark_processing"] = (time.perf_counter() - stage_started) * 1000
            self._set_progress(job_id, "발화 구간을 확인하고 있어요", 15)
            stage_started = time.perf_counter()
            speech_segments = self.vad_detector.detect(pending.path)
            stage_ms["vad"] = (time.perf_counter() - stage_started) * 1000
            if not speech_segments:
                self.repository.mark_failed(
                    user,
                    job_id,
                    "NO_SPEECH_DETECTED",
                    "음성이 인식되지 않았어요. 다시 녹음해 주세요.",
                )
                return
            self._set_progress(job_id, "음성을 전사하고 있어요", 35)
            stage_started = time.perf_counter()
            initial_prompt = self._stt_initial_prompt(user, pending)
            stage_ms["hint"] = (time.perf_counter() - stage_started) * 1000
            stage_started = time.perf_counter()
            if initial_prompt:
                result = self.transcriber.transcribe(
                    pending.path,
                    pending.source_id,
                    initial_prompt=initial_prompt,
                )
            else:
                result = self.transcriber.transcribe(pending.path, pending.source_id)
            stage_ms["stt"] = (time.perf_counter() - stage_started) * 1000
            self._set_progress(job_id, "말하기 속도와 침묵을 계산하고 있어요", 55)
            stage_started = time.perf_counter()
            delivery = self.delivery_analyzer.analyze(result, speech_segments)
            stage_ms["delivery"] = (time.perf_counter() - stage_started) * 1000
            result_payload = result.to_dict()
            # 내용 코칭은 사용자가 전사문을 수정·확정해 answer_revision을 만든 뒤에만
            # /api/agent에서 실행한다. STT 직후 원문으로 선행 코칭하지 않는다.
            self._set_progress(job_id, "결과를 정리하고 있어요", 95)
            stage_started = time.perf_counter()
            self.repository.mark_completed(user, job_id, result_payload, delivery.to_dict())
            stage_ms["persist"] = (time.perf_counter() - stage_started) * 1000
            self._set_progress(job_id, "분석을 완료했어요", 100)
            total_ms = (time.perf_counter() - process_started) * 1000
            logger.info(
                "analysis_timing job_id=%s audio_duration_sec=%.3f "
                "mark_processing_ms=%.1f vad_ms=%.1f hint_ms=%.1f "
                "stt_ms=%.1f delivery_ms=%.1f persist_ms=%.1f total_ms=%.1f",
                job_id,
                result.audio_duration_sec,
                stage_ms["mark_processing"],
                stage_ms["vad"],
                stage_ms["hint"],
                stage_ms["stt"],
                stage_ms["delivery"],
                stage_ms["persist"],
                total_ms,
            )
        except Exception:
            logger.exception("Analysis processing failed for job %s", job_id)
            try:
                self.repository.mark_failed(user, job_id, "ANALYSIS_FAILED", "분석에 실패했습니다. 다시 시도해 주세요.")
            except (SupabasePersistenceError, KeyError):
                pass
        finally:
            pending.path.unlink(missing_ok=True)
            with self._lock:
                self._pending.pop(job_id, None)

    def _stt_initial_prompt(
        self,
        user: AuthenticatedUser,
        pending: PendingAudio,
    ) -> str | None:
        loader = getattr(self.repository, "get_stt_hint_context", None)
        if not callable(loader):
            return None
        try:
            context = loader(user, pending.practice_session_id)
        except (KeyError, SupabasePersistenceError):
            logger.warning(
                "STT hint context unavailable for practice session %s",
                pending.practice_session_id,
            )
            return None
        hints = build_stt_prompt_hints(context)
        if hints.initial_prompt:
            logger.info(
                "STT initial prompt prepared from %s context terms",
                len(hints.terms),
            )
        return hints.initial_prompt

    def _improved_answer(
        self,
        job_id: str,
        user: AuthenticatedUser,
        pending: PendingAudio,
        transcript: str,
    ) -> dict[str, object]:
        generator = self.question_feedback_generator
        if generator is None:
            logger.warning("Question feedback generator is not configured for source %s", pending.source_id)
            return {}
        try:
            if pending.question_type == "preset":
                self._set_progress(job_id, "질문 기준을 불러오고 있어요", 76)
                rubric = generator.get_preset(pending.question_id or "")
                if not isinstance(rubric, dict):
                    logger.warning("No question feedback rubric for preset %s", pending.question_id)
                    return {}
                question = rubric.get("question")
                self._set_progress(job_id, "내용 피드백을 만들고 있어요", 84)
                feedback = generator.evaluate(transcript, rubric=rubric)
            else:
                question = pending.custom_question_text
                if not isinstance(question, str):
                    return {}
                rubric = self._previous_custom_rubric(user, pending)
                if rubric is None:
                    self._set_progress(job_id, "질문 기준을 만들고 있어요", 76)
                    rubric = generator.generate(question)
                self._set_progress(job_id, "내용 피드백을 만들고 있어요", 84)
                feedback = generator.evaluate(transcript, rubric=rubric)
            feedback_text = feedback.get("feedback") if isinstance(feedback, dict) else None
            if not isinstance(question, str) or not isinstance(feedback_text, str):
                logger.warning("Question feedback result is incomplete for source %s", pending.source_id)
                return {}
            stored_feedback = dict(feedback)
            if isinstance(rubric, dict) and isinstance(rubric.get("required_concepts"), list):
                stored_feedback["rubric"] = rubric
            generated = {
                "content_feedback": stored_feedback,
            }
            self._set_progress(job_id, "개선된 답변 예시를 만들고 있어요", 92)
            generated["improved_answer"] = generator.generate_example(question, transcript, feedback_text)
            logger.info("Question feedback generated for source %s", pending.source_id)
            return generated
        except (
            QuestionFeedbackInputError,
            QuestionFeedbackUnavailableError,
            QuestionRubricInputError,
            QuestionRubricUnavailableError,
        ) as error:
            cause = error.__cause__
            logger.warning(
                "Question feedback generation skipped for source %s: %s (%s)",
                pending.source_id,
                error.__class__.__name__,
                f"{cause.__class__.__name__}: {cause}" if cause else "no underlying error",
            )
            return {}

    def _previous_custom_rubric(
        self, user: AuthenticatedUser, pending: PendingAudio
    ) -> dict[str, object] | None:
        if pending.attempt_no != 2:
            return None
        try:
            first = self.repository.get_attempt_one(user, pending.practice_session_id)
        except KeyError:
            return None
        result = first.get("result")
        content_feedback = (
            result.get("content_feedback") if isinstance(result, dict) else None
        )
        rubric = (
            content_feedback.get("rubric")
            if isinstance(content_feedback, dict)
            else None
        )
        return rubric if isinstance(rubric, dict) else None

    def get(self, job_id: str, user: AuthenticatedUser) -> dict[str, object]:
        response = _to_api_job(self.repository.get_job(user, job_id))
        progress = self._get_progress(job_id)
        if progress:
            response["progress"] = progress
        return response

    def delete(self, job_id: str, user: AuthenticatedUser) -> None:
        self.repository.delete_job(user, job_id)
        with self._lock:
            pending = self._pending.pop(job_id, None)
            self._progress.pop(job_id, None)
        if pending:
            pending.path.unlink(missing_ok=True)

    def _set_progress(self, job_id: str, stage: str, percent: int) -> None:
        with self._lock:
            started_at = self._progress.get(job_id, {}).get("started_at", time.monotonic())
            self._progress[job_id] = {"stage": stage, "percent": percent, "started_at": started_at}

    def _get_progress(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            progress = self._progress.get(job_id)
            if progress is None:
                return None
            elapsed_seconds = max(0, round(time.monotonic() - float(progress["started_at"])))
            return {"stage": progress["stage"], "percent": progress["percent"], "elapsedSeconds": elapsed_seconds}

    def _validated_metadata(self, user: AuthenticatedUser, request: AnalysisRequest) -> dict[str, object]:
        if not request.source_id.strip():
            raise AudioValidationError("INVALID_SOURCE_ID", "source_id는 비어 있을 수 없습니다.")
        if request.question_type not in {"preset", "custom"} or request.attempt_no not in {1, 2}:
            raise AudioValidationError("INVALID_QUESTION", "질문 유형 또는 시도 횟수가 올바르지 않습니다.")
        question_id = request.question_id.strip() if request.question_id else None
        custom_text = request.custom_question_text.strip() if request.custom_question_text else None
        if request.question_type == "preset":
            if not question_id or custom_text:
                raise AudioValidationError("INVALID_QUESTION", "preset 질문에는 question_id가 필요합니다.")
            custom_text = None
        elif not custom_text or len(custom_text) > 200 or question_id:
            raise AudioValidationError("INVALID_QUESTION", "custom 질문은 1~200자 질문만 사용할 수 있습니다.")

        if request.attempt_no == 1:
            if request.practice_session_id:
                try:
                    practice_session_id = str(UUID(request.practice_session_id))
                    practice_session = self.repository.get_practice_session(
                        user, practice_session_id
                    )
                except (ValueError, KeyError):
                    raise AudioValidationError(
                        "INVALID_PRACTICE_SESSION",
                        "선택한 공고와 질문의 연습 세션을 찾을 수 없습니다.",
                    ) from None
                if (
                    practice_session.get("question_type") != request.question_type
                    or practice_session.get("question_id") != question_id
                    or practice_session.get("custom_question_text") != custom_text
                ):
                    raise AudioValidationError(
                        "INVALID_PRACTICE_SESSION",
                        "연습 세션에 고정된 질문과 녹음 질문이 다릅니다.",
                    )
            else:
                # 기존 클라이언트와 로컬 분석 테스트는 공고 선택 기능을 붙이기 전
                # 요청 형식을 계속 사용할 수 있게 서버에서 세션 ID를 만든다.
                practice_session_id = str(uuid4())
        else:
            try:
                practice_session_id = str(UUID(request.practice_session_id or ""))
                first = self.repository.get_attempt_one(user, practice_session_id)
            except (ValueError, KeyError):
                raise AudioValidationError("INVALID_QUESTION", "같은 질문의 첫 번째 시도가 필요합니다.") from None
            if first.get("question_type") != request.question_type or first.get("question_id") != question_id or first.get("custom_question_text") != custom_text:
                raise AudioValidationError("INVALID_QUESTION", "재녹음은 첫 번째 시도와 같은 질문이어야 합니다.")
        return {
            "source_id": request.source_id.strip(), "practice_session_id": practice_session_id,
            "question_type": request.question_type, "question_id": question_id,
            "custom_question_text": custom_text, "attempt_no": request.attempt_no, "status": "queued",
        }

    def _write_validated_audio(self, filename: str, content: bytes) -> Path:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_AUDIO_SUFFIXES:
            raise AudioValidationError("INVALID_FORMAT", "WAV, WebM, MP3, MP4/M4A, OGG 파일만 분석할 수 있습니다.")
        if not content:
            raise AudioValidationError("INVALID_AUDIO", "비어 있는 음성 파일입니다.")
        if len(content) > MAX_AUDIO_BYTES:
            raise AudioValidationError("FILE_TOO_LARGE", "음성 파일은 15MB 이하여야 합니다.")
        self.working_dir.mkdir(parents=True, exist_ok=True)
        temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=suffix, prefix="analysis-", dir=self.working_dir, delete=False)
        path = Path(temp_file.name)
        try:
            with temp_file:
                temp_file.write(content)
            duration = self._probe_duration(path)
            if not MIN_AUDIO_DURATION_SEC <= duration <= MAX_AUDIO_DURATION_SEC:
                raise AudioValidationError("INVALID_DURATION", "음성 길이는 5초 이상 60초 이하여야 합니다.")
            return path
        except Exception:
            path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _probe_duration(path: Path) -> float:
        if path.suffix.lower() == ".wav":
            try:
                with wave.open(str(path), "rb") as audio:
                    rate = audio.getframerate()
                    if rate <= 0:
                        raise AudioValidationError("INVALID_AUDIO", "음성 파일을 읽을 수 없습니다.")
                    return audio.getnframes() / rate
            except (wave.Error, EOFError) as error:
                raise AudioValidationError("INVALID_AUDIO", "음성 파일을 읽을 수 없습니다.") from error
        try:
            import av
            with av.open(str(path)) as container:
                if container.duration is not None:
                    return float(container.duration / av.time_base)

                # Safari 녹음 MP4처럼 컨테이너 메타데이터에 전체 길이가 없는 경우에도
                # 디코딩 가능한 오디오 프레임으로 실제 길이를 계산한다.
                duration = 0.0
                for frame in container.decode(audio=0):
                    sample_rate = getattr(frame, "sample_rate", 0)
                    samples = getattr(frame, "samples", 0)
                    if sample_rate and samples:
                        duration += samples / sample_rate
                if duration > 0:
                    return duration
                raise AudioValidationError("INVALID_AUDIO", "음성 길이를 확인할 수 없습니다.")
        except AudioValidationError:
            raise
        except Exception as error:
            raise AudioValidationError("INVALID_AUDIO", "음성 파일을 읽을 수 없습니다.") from error


def _to_api_job(row: dict[str, object]) -> dict[str, object]:
    result = row.get("result")
    if isinstance(result, dict):
        # 대화는 만료·revision 검증을 거치는 연습기록 API에서만 노출한다.
        result = {key: value for key, value in result.items() if key != "interview_chat"}
    return {"job_id": row.get("id"), "source_id": row.get("source_id"), "practice_session_id": row.get("practice_session_id"), "attempt_no": row.get("attempt_no"), "status": row.get("status"), "result": result, "delivery": row.get("delivery"), "error": row.get("error")}
