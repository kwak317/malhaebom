"""별도 GPU Worker를 질문 TTS 계약에 연결하는 synthesizer."""

from __future__ import annotations

import base64
import binascii
import io
import json
import threading
import wave
from collections.abc import Iterator
from typing import Any

from app.services.coach_tts import CoachTtsUnavailableError, TtsWorkerClient
from app.services.question_tts import (
    GeneratedQuestionAudio,
    QuestionTtsUnavailableError,
    prepare_synthesis_text,
)
from app.services.question_tts_stream import GeneratedQuestionPcm


class RemoteQuestionTtsSynthesizer:
    """GPU Worker PCM을 기존 저장·소유권 서비스에 전달한다."""

    def __init__(self, client: TtsWorkerClient | None = None) -> None:
        self.client = client or TtsWorkerClient()

    def warmup(self) -> None:
        if not self.client.is_ready():
            raise QuestionTtsUnavailableError()

    def synthesize(self, question: str) -> GeneratedQuestionAudio:
        try:
            wav_bytes = self.client.synthesize(prepare_synthesis_text(question))
            with wave.open(io.BytesIO(wav_bytes), "rb") as source:
                duration_ms = round(
                    source.getnframes() / source.getframerate() * 1000
                )
        except (CoachTtsUnavailableError, EOFError, wave.Error, ZeroDivisionError) as error:
            raise QuestionTtsUnavailableError() from error
        return GeneratedQuestionAudio(wav_bytes=wav_bytes, duration_ms=duration_ms)

    def stream(
        self,
        synthesis_text: str,
        cancel: threading.Event,
    ) -> Iterator[GeneratedQuestionPcm]:
        pending: bytes | None = None
        started = False
        expected_sequence = 0
        completed = False
        buffer = b""
        try:
            chunks = self.client.synthesize_pcm_stream(synthesis_text)
            for chunk in chunks:
                if cancel.is_set():
                    return
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    event = _parse_event(line)
                    if completed:
                        raise QuestionTtsUnavailableError()
                    event_type = event.get("type")
                    if event_type == "start":
                        if (
                            started
                            or event.get("format") != "pcm_s16le"
                            or event.get("sampleRate") != 24_000
                            or event.get("channels") != 1
                        ):
                            raise QuestionTtsUnavailableError()
                        started = True
                    elif event_type == "audio":
                        if not started or event.get("sequence") != expected_sequence:
                            raise QuestionTtsUnavailableError()
                        pcm16 = _decode_pcm16(event.get("pcmBase64"))
                        if pending is not None:
                            yield GeneratedQuestionPcm(pcm16=pending, is_final=False)
                        pending = pcm16
                        expected_sequence += 1
                    elif event_type == "complete":
                        if not started or pending is None:
                            raise QuestionTtsUnavailableError()
                        yield GeneratedQuestionPcm(pcm16=pending, is_final=True)
                        pending = None
                        completed = True
                    else:
                        raise QuestionTtsUnavailableError()
            if buffer.strip() or not completed or pending is not None:
                raise QuestionTtsUnavailableError()
        except (CoachTtsUnavailableError, QuestionTtsUnavailableError):
            raise
        except Exception as error:
            raise QuestionTtsUnavailableError() from error


def _parse_event(line: bytes) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise QuestionTtsUnavailableError() from error
    if not isinstance(value, dict):
        raise QuestionTtsUnavailableError()
    return value


def _decode_pcm16(value: Any) -> bytes:
    if not isinstance(value, str):
        raise QuestionTtsUnavailableError()
    try:
        pcm16 = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise QuestionTtsUnavailableError() from error
    if not pcm16 or len(pcm16) % 2:
        raise QuestionTtsUnavailableError()
    return pcm16
