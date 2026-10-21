from __future__ import annotations

import io
import threading
import wave
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from app.services.question_tts import (
    GeneratedQuestionAudio,
    QuestionTtsRepository,
    QuestionTtsUnavailableError,
    normalize_question,
    prepare_synthesis_text,
    validate_question_wav,
)
from app.services.question_tts_persistence import QuestionTtsPersistenceError, QuestionTtsRecord


SAMPLE_RATE = 24_000
CHANNELS = 1
QUIET_RMS_DB = -35.0
QUIET_TAIL_SECONDS = 0.5


@dataclass(frozen=True)
class GeneratedQuestionPcm:
    pcm16: bytes
    sample_rate: int = SAMPLE_RATE
    channels: int = CHANNELS
    is_final: bool = False


@dataclass(frozen=True)
class StreamStart:
    text: str
    sample_rate: int = SAMPLE_RATE
    channels: int = CHANNELS
    format: str = "pcm_s16le"


@dataclass(frozen=True)
class StreamAudio:
    sequence: int
    pcm16: bytes


@dataclass(frozen=True)
class StreamComplete:
    record: QuestionTtsRecord


@dataclass(frozen=True)
class StreamError:
    code: str
    message: str


QuestionTtsStreamEvent = StreamStart | StreamAudio | StreamComplete | StreamError


class QuestionTtsStreamSynthesizer(Protocol):
    def stream(self, synthesis_text: str, cancel: threading.Event) -> Iterator[GeneratedQuestionPcm]: ...


def pcm16_rms_db(chunk: bytes) -> float:
    if not isinstance(chunk, bytes) or not chunk or len(chunk) % 2:
        raise QuestionTtsUnavailableError()
    samples = np.frombuffer(chunk, dtype="<i2").astype(np.float32) / 32_768.0
    return float(20 * np.log10(np.sqrt(np.mean(np.square(samples))) + 1e-12))


class QuestionTtsStreamService:
    def __init__(
        self,
        synthesizer: QuestionTtsStreamSynthesizer,
        repository: QuestionTtsRepository,
    ) -> None:
        self.synthesizer = synthesizer
        self.repository = repository

    def ensure_ready(self) -> None:
        return None

    def events(
        self,
        user: Any,
        raw_question: str,
        cancel: threading.Event,
    ) -> Iterator[QuestionTtsStreamEvent]:
        text = normalize_question(raw_question)
        if cancel.is_set():
            return

        yield StreamStart(text=text)
        generator: Iterator[GeneratedQuestionPcm] | None = None
        chunks: list[bytes] = []
        saw_active_audio = False
        quiet_seconds = 0.0
        stopped_by_quiet_tail = False
        final_chunk_received = False

        try:
            generator = self.synthesizer.stream(prepare_synthesis_text(text), cancel)
            for chunk in generator:
                if cancel.is_set():
                    _close_generator(generator)
                    return
                _validate_pcm(chunk)
                chunks.append(chunk.pcm16)
                final_chunk_received = chunk.is_final
                yield StreamAudio(sequence=len(chunks) - 1, pcm16=chunk.pcm16)

                if pcm16_rms_db(chunk.pcm16) > QUIET_RMS_DB:
                    saw_active_audio = True
                    quiet_seconds = 0.0
                elif saw_active_audio:
                    quiet_seconds += len(chunk.pcm16) / (SAMPLE_RATE * 2)
                    if quiet_seconds >= QUIET_TAIL_SECONDS:
                        stopped_by_quiet_tail = True
                        _close_generator(generator)
                        break

            if cancel.is_set():
                _close_generator(generator)
                return
            if not chunks:
                raise QuestionTtsUnavailableError()
            if not stopped_by_quiet_tail and not final_chunk_received:
                raise QuestionTtsUnavailableError()

            pcm16 = b"".join(chunks)
            duration_ms = round(len(pcm16) / (SAMPLE_RATE * 2) * 1000)
            audio = GeneratedQuestionAudio(_pcm16_to_wav(pcm16), duration_ms)
            validate_question_wav(audio.wav_bytes, audio.duration_ms)
            record = self.repository.create(user, audio)
            yield StreamComplete(record)
        except (QuestionTtsPersistenceError, QuestionTtsUnavailableError):
            yield StreamError(
                code="TTS_GENERATION_FAILED",
                message="질문 음성을 만들지 못했습니다. 다시 시도해 주세요.",
            )
        except Exception:
            yield StreamError(
                code="TTS_GENERATION_FAILED",
                message="질문 음성을 만들지 못했습니다. 다시 시도해 주세요.",
            )
        finally:
            if cancel.is_set() and generator is not None:
                _close_generator(generator)


def _validate_pcm(chunk: GeneratedQuestionPcm) -> None:
    if (
        not isinstance(chunk, GeneratedQuestionPcm)
        or chunk.sample_rate != SAMPLE_RATE
        or chunk.channels != CHANNELS
    ):
        raise QuestionTtsUnavailableError()
    pcm16_rms_db(chunk.pcm16)


def _pcm16_to_wav(pcm16: bytes) -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(CHANNELS)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm16)
    return stream.getvalue()


def _close_generator(generator: Iterator[GeneratedQuestionPcm]) -> None:
    close = getattr(generator, "close", None)
    if callable(close):
        close()
