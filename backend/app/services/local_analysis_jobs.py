from __future__ import annotations

import os
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Protocol
from uuid import uuid4

from app.schemas.delivery import DeliveryAnalysisResult
from app.schemas.stt import SttResult
from app.services.delivery_analysis import DeliveryAnalyzer
from app.services.stt_transcriber import SUPPORTED_AUDIO_SUFFIXES
from app.services.vad_detector import SileroVadDetector, SpeechSegmentDetector


MAX_AUDIO_BYTES = 15 * 1024 * 1024
MIN_AUDIO_DURATION_SEC = 5.0
MAX_AUDIO_DURATION_SEC = 60.0


class AudioValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Transcriber(Protocol):
    def transcribe(
        self,
        audio_path: Path | str,
        source_id: str,
        *,
        initial_prompt: str | None = None,
    ) -> SttResult: ...


@dataclass
class LocalAnalysisJob:
    job_id: str
    user_id: str
    source_id: str
    audio_path: Path
    status: str
    created_at: float
    result: SttResult | None = None
    delivery: DeliveryAnalysisResult | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "source_id": self.source_id,
            "status": self.status,
            "result": self.result.to_dict() if self.result else None,
            "delivery": self.delivery.to_dict() if self.delivery else None,
            "error": (
                {"code": self.error_code, "message": self.error_message}
                if self.error_code
                else None
            ),
        }


class LocalAnalysisJobService:
    """Local-only transient analysis jobs. This is not a persistence layer."""

    def __init__(
        self,
        transcriber: Transcriber,
        working_dir: Path | str | None = None,
        vad_detector: SpeechSegmentDetector | None = None,
        delivery_analyzer: DeliveryAnalyzer | None = None,
    ) -> None:
        self.transcriber = transcriber
        self.vad_detector = vad_detector or SileroVadDetector()
        self.delivery_analyzer = delivery_analyzer or DeliveryAnalyzer()
        self.working_dir = Path(
            working_dir or os.getenv("LOCAL_ANALYSIS_DIR", "local-analysis")
        )
        self._jobs: dict[str, LocalAnalysisJob] = {}
        self._lock = Lock()

    def create_job(
        self, source_id: str, filename: str, content: bytes, user_id: str = ""
    ) -> LocalAnalysisJob:
        if not source_id.strip():
            raise AudioValidationError("INVALID_SOURCE_ID", "source_id는 비어 있을 수 없습니다.")
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_AUDIO_SUFFIXES:
            raise AudioValidationError(
                "INVALID_FORMAT", "WAV, WebM, MP3, MP4/M4A, OGG 파일만 분석할 수 있습니다."
            )
        if not content:
            raise AudioValidationError("INVALID_AUDIO", "비어 있는 음성 파일입니다.")
        if len(content) > MAX_AUDIO_BYTES:
            raise AudioValidationError("FILE_TOO_LARGE", "음성 파일은 15MB 이하여야 합니다.")

        self.working_dir.mkdir(parents=True, exist_ok=True)
        temp_file = tempfile.NamedTemporaryFile(
            mode="wb", suffix=suffix, prefix="analysis-", dir=self.working_dir, delete=False
        )
        path = Path(temp_file.name)
        try:
            with temp_file:
                temp_file.write(content)
            duration = self._probe_duration(path)
            if not MIN_AUDIO_DURATION_SEC <= duration <= MAX_AUDIO_DURATION_SEC:
                raise AudioValidationError(
                    "INVALID_DURATION", "음성 길이는 5초 이상 60초 이하여야 합니다."
                )
        except Exception:
            path.unlink(missing_ok=True)
            raise

        job = LocalAnalysisJob(
            job_id=str(uuid4()),
            user_id=user_id,
            source_id=source_id.strip(),
            audio_path=path,
            status="queued",
            created_at=time.time(),
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def process(self, job_id: str) -> LocalAnalysisJob:
        job = self.get(job_id)
        with self._lock:
            if job.status != "queued":
                return job
            job.status = "processing"

        try:
            vad_segments = self.vad_detector.detect(job.audio_path)
        except Exception:
            self._fail(job, "ANALYSIS_FAILED", "전달력 분석에 실패했습니다. 다시 시도해 주세요.")
        else:
            if not vad_segments:
                self._fail(job, "NO_SPEECH_DETECTED", "음성이 인식되지 않았어요. 다시 녹음해 주세요.")
            else:
                try:
                    result = self.transcriber.transcribe(job.audio_path, job.source_id)
                except Exception:
                    self._fail(job, "STT_FAILED", "음성 전사에 실패했습니다. 다시 시도해 주세요.")
                else:
                    try:
                        delivery = self.delivery_analyzer.analyze(result, vad_segments)
                    except Exception:
                        self._fail(job, "ANALYSIS_FAILED", "전달력 분석에 실패했습니다. 다시 시도해 주세요.")
                    else:
                        with self._lock:
                            job.status = "completed"
                            job.result = result
                            job.delivery = delivery
        finally:
            job.audio_path.unlink(missing_ok=True)
        return job

    def _fail(self, job: LocalAnalysisJob, code: str, message: str) -> None:
        with self._lock:
            job.status = "failed"
            job.error_code = code
            job.error_message = message

    def get(self, job_id: str, user_id: str | None = None) -> LocalAnalysisJob:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None or (user_id is not None and job.user_id != user_id):
            raise KeyError(job_id)
        return job

    @staticmethod
    def _probe_duration(path: Path) -> float:
        if path.suffix.lower() == ".wav":
            try:
                with wave.open(str(path), "rb") as audio:
                    frame_rate = audio.getframerate()
                    if frame_rate <= 0:
                        raise AudioValidationError("INVALID_AUDIO", "음성 파일을 읽을 수 없습니다.")
                    return audio.getnframes() / frame_rate
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
