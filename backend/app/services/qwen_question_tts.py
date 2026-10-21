from __future__ import annotations

import io
import os
import threading
import wave
from collections.abc import Callable, Iterator
from typing import Any

import numpy as np

from app.core.question_tts_settings import QuestionTtsSettings
from app.services.question_tts import (
    GeneratedQuestionAudio,
    QuestionTtsUnavailableError,
    prepare_synthesis_text,
    validate_question_wav,
)
from app.services.question_tts_stream import GeneratedQuestionPcm


QUESTIONER_SPEAKER = "candidate_04_questioner"
SAMPLE_RATE = 24_000


class QwenQuestionTtsSynthesizer:
    def __init__(self, model: Any) -> None:
        self.model = model
        self._warmed = False

    @classmethod
    def from_settings(
        cls,
        settings: QuestionTtsSettings,
        *,
        model_loader: Callable[..., Any] | None = None,
        cuda_available: Callable[[], bool] | None = None,
        bfloat16: Any | None = None,
    ) -> "QwenQuestionTtsSynthesizer":
        active_cuda_available = cuda_available or _cuda_available
        if not active_cuda_available():
            raise QuestionTtsUnavailableError()
        active_model_loader = model_loader or _load_local_qwen_model
        active_bfloat16 = _bfloat16() if bfloat16 is None else bfloat16
        try:
            model = active_model_loader(
                str(settings.model_path),
                device="cuda:0",
                dtype=active_bfloat16,
                attn_implementation="sdpa",
                max_seq_len=2048,
                local_files_only=True,
            )
            if QUESTIONER_SPEAKER not in model.model.get_supported_speakers():
                raise QuestionTtsUnavailableError()
            model.predictor_graph.do_sample = False
        except QuestionTtsUnavailableError:
            raise
        except Exception as error:
            raise QuestionTtsUnavailableError() from error
        return cls(model)

    def warmup(self) -> None:
        if self._warmed:
            return
        generator: Iterator[tuple[Any, int, dict[str, Any]]] | None = None
        try:
            self.model.warmup(prefill_len=100)
            generator = self._runtime_stream("준비합니다.//", max_new_tokens=6)
            for _ in generator:
                pass
        except Exception as error:
            raise QuestionTtsUnavailableError() from error
        finally:
            _close_generator(generator)
        self._warmed = True

    def stream(
        self,
        synthesis_text: str,
        cancel: threading.Event,
    ) -> Iterator[GeneratedQuestionPcm]:
        generator: Iterator[tuple[Any, int, dict[str, Any]]] | None = None
        pending: tuple[Any, int, dict[str, Any]] | None = None
        try:
            generator = self._runtime_stream(synthesis_text, max_new_tokens=512)
            for waveform, sample_rate, timing in generator:
                if cancel.is_set():
                    _close_generator(generator)
                    return
                if pending is not None:
                    yield _to_pcm_chunk(*pending, is_final=False)
                pending = waveform, sample_rate, timing
            if pending is not None:
                waveform, sample_rate, timing = pending
                yield _to_pcm_chunk(
                    waveform,
                    sample_rate,
                    timing,
                    is_final=_ended_before_max_new_tokens(timing, max_new_tokens=512),
                )
        except QuestionTtsUnavailableError:
            raise
        except Exception as error:
            raise QuestionTtsUnavailableError() from error
        finally:
            _close_generator(generator)

    def synthesize(self, question: str) -> GeneratedQuestionAudio:
        try:
            chunks = list(self.stream(prepare_synthesis_text(question), threading.Event()))
            if not chunks or not chunks[-1].is_final:
                raise QuestionTtsUnavailableError()
            pcm16 = b"".join(chunk.pcm16 for chunk in chunks)
            duration_ms = round(len(pcm16) / (SAMPLE_RATE * 2) * 1000)
            wav_bytes = _pcm16_to_wav(pcm16)
            validate_question_wav(wav_bytes, duration_ms)
        except QuestionTtsUnavailableError:
            raise
        except Exception as error:
            raise QuestionTtsUnavailableError() from error
        return GeneratedQuestionAudio(wav_bytes, duration_ms)

    def _runtime_stream(
        self,
        text: str,
        *,
        max_new_tokens: int,
    ) -> Iterator[tuple[Any, int, dict[str, Any]]]:
        return self.model.generate_custom_voice_streaming(
            text=text,
            speaker=QUESTIONER_SPEAKER,
            language="Korean",
            non_streaming_mode=True,
            do_sample=False,
            max_new_tokens=max_new_tokens,
            chunk_size=6,
        )


def _to_pcm_chunk(
    waveform: Any,
    sample_rate: int,
    timing: Any,
    *,
    is_final: bool,
) -> GeneratedQuestionPcm:
    if sample_rate != SAMPLE_RATE or not isinstance(timing, dict):
        raise QuestionTtsUnavailableError()
    values = np.asarray(waveform, dtype=np.float32)
    if values.ndim != 1 or values.size < 1 or not np.isfinite(values).all():
        raise QuestionTtsUnavailableError()
    pcm16 = np.rint(np.clip(values, -1.0, 1.0) * 32_767.0).astype("<i2").tobytes()
    return GeneratedQuestionPcm(pcm16=pcm16, is_final=is_final)


def _ended_before_max_new_tokens(timing: dict[str, Any], *, max_new_tokens: int) -> bool:
    total_steps = timing.get("total_steps_so_far")
    if not isinstance(total_steps, int) or total_steps < 1:
        raise QuestionTtsUnavailableError()
    return total_steps < max_new_tokens


def _pcm16_to_wav(pcm16: bytes) -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm16)
    return stream.getvalue()


def _close_generator(generator: Any) -> None:
    close = getattr(generator, "close", None)
    if callable(close):
        close()


def _load_local_qwen_model(path: str, **kwargs: Any) -> Any:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from faster_qwen3_tts import FasterQwen3TTS

    return FasterQwen3TTS.from_pretrained(path, **kwargs)


def _cuda_available() -> bool:
    import torch

    return bool(torch.cuda.is_available())


def _bfloat16() -> Any:
    import torch

    return torch.bfloat16
