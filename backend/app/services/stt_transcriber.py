from __future__ import annotations

import time
import os
import unicodedata
from collections.abc import Callable, Iterable
from pathlib import Path
from threading import Lock
from typing import Any, Protocol

from app.core.stt_settings import SttSettings
from app.schemas.stt import (
    FillerAnalysis,
    FillerOccurrence,
    SegmentTranscript,
    SttResult,
    WordTiming,
)


SUPPORTED_AUDIO_SUFFIXES = frozenset({".wav", ".webm", ".mp3", ".mp4", ".m4a", ".ogg"})
DEFAULT_FILLERS = ("음", "어")


class WhisperBackend(Protocol):
    def transcribe(self, audio: str, **kwargs: Any) -> tuple[Iterable[Any], Any]: ...


def normalize_token(token: str) -> str:
    normalized = unicodedata.normalize("NFKC", token).strip()
    return "".join(
        character
        for character in normalized
        if not unicodedata.category(character).startswith(("P", "S"))
    )


def analyze_fillers(
    words: list[WordTiming], fillers: tuple[str, ...] = DEFAULT_FILLERS
) -> FillerAnalysis:
    occurrences: dict[str, list[FillerOccurrence]] = {
        filler: [] for filler in fillers
    }
    for word in words:
        token = normalize_token(word.word)
        if token not in occurrences:
            continue
        occurrences[token].append(
            FillerOccurrence(
                start=word.start,
                end=word.end,
                duration=round(word.end - word.start, 3),
                probability=word.probability,
            )
        )

    counts = {token: len(items) for token, items in occurrences.items()}
    return FillerAnalysis(
        counts=counts,
        total_count=sum(counts.values()),
        occurrences=occurrences,
    )


class FasterWhisperTranscriber:
    def __init__(
        self,
        settings: SttSettings | None = None,
        model_factory: Callable[[SttSettings], WhisperBackend] | None = None,
    ) -> None:
        self.settings = settings or SttSettings.from_env()
        self._model_factory = model_factory or self._default_model_factory
        self._model: WhisperBackend | None = None
        self._model_lock = Lock()
        self._remote = None
        remote_url = os.getenv("STT_REMOTE_URL", "").strip()
        if remote_url and model_factory is None:
            from app.services.remote_stt import RemoteSttTranscriber

            self._remote = RemoteSttTranscriber(remote_url)

    @staticmethod
    def _default_model_factory(settings: SttSettings) -> WhisperBackend:
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise RuntimeError(
                "faster-whisper가 설치되지 않았습니다. "
                "backend/requirements-stt.txt를 설치하세요."
            ) from error

        return WhisperModel(
            settings.model_name,
            device=settings.device,
            compute_type=settings.compute_type,
        )

    @property
    def model(self) -> WhisperBackend:
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    self._model = self._model_factory(self.settings)
        return self._model

    def warmup(self) -> None:
        """첫 분석 전에 모델을 메모리에 올려 사용자 대기 시간을 줄인다."""
        if self._remote is not None:
            self._remote.warmup()
            return
        _ = self.model

    def transcribe(
        self,
        audio_path: Path | str,
        source_id: str,
        *,
        initial_prompt: str | None = None,
    ) -> SttResult:
        path = Path(audio_path).expanduser().resolve()
        self._validate_input(path, source_id)

        if self._remote is not None:
            return self._remote.transcribe(path, source_id, initial_prompt=initial_prompt)

        model = self.model
        started_at = time.perf_counter()
        transcribe_kwargs: dict[str, Any] = {
            "language": "ko",
            "task": "transcribe",
            "beam_size": self.settings.beam_size,
            "temperature": 0.0,
            "word_timestamps": True,
            "vad_filter": False,
            "condition_on_previous_text": False,
        }
        if initial_prompt and initial_prompt.strip():
            transcribe_kwargs["initial_prompt"] = initial_prompt.strip()
        segment_stream, info = model.transcribe(
            str(path),
            **transcribe_kwargs,
        )
        raw_segments = list(segment_stream)
        processing_time = time.perf_counter() - started_at

        segments: list[SegmentTranscript] = []
        words: list[WordTiming] = []
        for segment in raw_segments:
            segment_words = [self._convert_word(word) for word in (segment.words or [])]
            words.extend(segment_words)
            segments.append(
                SegmentTranscript(
                    start=round(float(segment.start), 3),
                    end=round(float(segment.end), 3),
                    text=str(segment.text).strip(),
                    words=segment_words,
                )
            )

        duration = round(float(getattr(info, "duration", 0.0)), 3)
        language_probability = getattr(info, "language_probability", None)
        return SttResult(
            source_id=source_id,
            model=self.settings.model_name,
            device=self.settings.device,
            compute_type=self.settings.compute_type,
            language=str(getattr(info, "language", "ko")),
            language_probability=(
                round(float(language_probability), 4)
                if language_probability is not None
                else None
            ),
            audio_duration_sec=duration,
            processing_time_sec=round(processing_time, 3),
            rtf=round(processing_time / duration, 4) if duration > 0 else None,
            text=" ".join(item.text for item in segments).strip(),
            fillers=analyze_fillers(words),
            segments=segments,
            words=words,
        )

    @staticmethod
    def _validate_input(path: Path, source_id: str) -> None:
        if not source_id.strip():
            raise ValueError("source_id는 비어 있을 수 없습니다.")
        if not path.is_file():
            raise FileNotFoundError(f"음성 파일을 찾을 수 없습니다: {path.name}")
        if path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
            raise ValueError(
                "지원하지 않는 음성 형식입니다. WAV, WebM, MP3만 사용할 수 있습니다."
            )

    @staticmethod
    def _convert_word(word: Any) -> WordTiming:
        probability = getattr(word, "probability", None)
        return WordTiming(
            word=str(word.word).strip(),
            start=round(float(word.start), 3),
            end=round(float(word.end), 3),
            probability=(round(float(probability), 4) if probability is not None else None),
        )
