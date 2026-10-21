from __future__ import annotations

import io
import re
import unicodedata
import wave
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.services.question_tts_persistence import QuestionTtsPersistenceError, QuestionTtsRecord


class QuestionTtsInputError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class QuestionTtsUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedQuestionAudio:
    wav_bytes: bytes
    duration_ms: int


@dataclass(frozen=True)
class QuestionTtsCreation:
    record: QuestionTtsRecord
    text: str


class QuestionTtsSynthesizer(Protocol):
    def synthesize(self, question: str) -> GeneratedQuestionAudio: ...


class QuestionTtsRepository(Protocol):
    def create(self, user: Any, audio: GeneratedQuestionAudio) -> QuestionTtsRecord: ...

    def read_wav(self, user: Any, audio_id: str, now: datetime) -> bytes: ...


def normalize_question(raw: str) -> str:
    if not isinstance(raw, str):
        raise QuestionTtsInputError("질문은 문자열로 입력해 주세요.")
    normalized = raw.strip()
    non_whitespace_length = len(re.sub(r"\s+", "", normalized))
    if not 1 <= non_whitespace_length <= 200:
        raise QuestionTtsInputError("질문은 공백 제외 1자 이상 200자 이하로 입력해 주세요.")
    if any(unicodedata.category(character).startswith("C") for character in normalized):
        raise QuestionTtsInputError("질문에 사용할 수 없는 문자가 포함되어 있습니다.")
    if re.search(r"<[^>]+>", normalized):
        raise QuestionTtsInputError("질문에 HTML 태그를 넣을 수 없습니다.")
    return normalized


def prepare_synthesis_text(normalized_question: str) -> str:
    return f"{normalized_question}//"


def validate_question_wav(content: bytes, duration_ms: int) -> None:
    if not isinstance(content, bytes) or not content or not isinstance(duration_ms, int) or duration_ms < 1:
        raise QuestionTtsUnavailableError()
    try:
        with wave.open(io.BytesIO(content), "rb") as source:
            if (
                source.getframerate() != 24_000
                or source.getnchannels() != 1
                or source.getsampwidth() != 2
                or source.getcomptype() != "NONE"
                or source.getnframes() < 1
            ):
                raise QuestionTtsUnavailableError()
            measured_duration_ms = round(source.getnframes() / source.getframerate() * 1000)
    except (EOFError, wave.Error) as error:
        raise QuestionTtsUnavailableError() from error
    if abs(measured_duration_ms - duration_ms) > 100:
        raise QuestionTtsUnavailableError()


class QuestionTtsService:
    def __init__(self, synthesizer: QuestionTtsSynthesizer, repository: QuestionTtsRepository) -> None:
        self.synthesizer = synthesizer
        self.repository = repository

    def create(self, user: Any, raw_question: str) -> QuestionTtsCreation:
        text = normalize_question(raw_question)
        try:
            audio = self.synthesizer.synthesize(text)
            validate_question_wav(audio.wav_bytes, audio.duration_ms)
            record = self.repository.create(user, audio)
        except QuestionTtsInputError:
            raise
        except (QuestionTtsPersistenceError, QuestionTtsUnavailableError) as error:
            raise QuestionTtsUnavailableError() from error
        except Exception as error:
            raise QuestionTtsUnavailableError() from error
        return QuestionTtsCreation(record, text)

    def read(self, user: Any, audio_id: str, now: datetime) -> bytes:
        try:
            return self.repository.read_wav(user, audio_id, now)
        except KeyError:
            raise
        except QuestionTtsPersistenceError as error:
            raise QuestionTtsUnavailableError() from error
