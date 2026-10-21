from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import re
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from faster_qwen3_tts import FasterQwen3TTS

MODEL_PATH = os.getenv("TTS_WORKER_MODEL_PATH", "").strip()
TTS_SPEAKER = os.getenv("TTS_WORKER_SPEAKER", "candidate_04_questioner").strip() or "candidate_04_questioner"
TTS_INSTRUCT = "차분하고 전문적인 한국어 면접 질문자처럼 또렷하게, 문장 사이에 긴 공백을 두지 말고 짧은 호흡으로 자연스럽게 이어 말해 주세요."
TTS_CACHE_SIZE = 16
STREAM_CHUNK_MAX_CHARS = 32
PCM_TAIL_FADE_MS = 30
PCM_TAIL_SILENCE_MS = 200

logger = logging.getLogger("uvicorn.error")

HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?。！？])\s+|\n+")


class TtsRequest(BaseModel):
    question: str


def normalize_question(question: str) -> str:
    normalized = question.strip()

    if not normalized or len(normalized) > 300:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="질문은 1자 이상 300자 이하로 입력해 주세요.",
        )

    if "\x00" in normalized or CONTROL_CHAR_PATTERN.search(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="허용되지 않는 문자가 포함되어 있습니다.",
        )

    if HTML_TAG_PATTERN.search(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HTML 태그는 입력할 수 없습니다.",
        )

    return normalized


def split_sentences(text: str) -> list[str]:
    sentences = [sentence.strip() for sentence in SENTENCE_BOUNDARY_PATTERN.split(text) if sentence.strip()]
    chunks: list[str] = []
    for sentence in sentences or [text]:
        words = sentence.split()
        current_chunk = ""
        for word in words:
            candidate = f"{current_chunk} {word}".strip()
            if current_chunk and len(candidate) > STREAM_CHUNK_MAX_CHARS:
                chunks.append(current_chunk)
                current_chunk = word
            else:
                current_chunk = candidate
        if current_chunk:
            chunks.append(current_chunk)
    return chunks


def cache_audio(text: str, audio: tuple[bytes, int, int]) -> None:
    app.state.audio_cache[text] = audio
    app.state.audio_cache.move_to_end(text)
    if len(app.state.audio_cache) > TTS_CACHE_SIZE:
        app.state.audio_cache.popitem(last=False)


def next_stream_chunk(generator: Any) -> tuple[Any, int, dict[str, Any]] | None:
    try:
        with torch.inference_mode():
            return next(generator)
    except StopIteration:
        return None


def waveform_to_pcm16(waveform: Any, sample_rate: int) -> bytes:
    if sample_rate != 24_000:
        raise RuntimeError(f"지원하지 않는 샘플레이트입니다: {sample_rate}")
    samples = np.asarray(waveform, dtype=np.float32)
    if samples.ndim != 1 or not samples.size or not np.isfinite(samples).all():
        raise RuntimeError("유효하지 않은 PCM 파형입니다.")
    return np.rint(np.clip(samples, -1.0, 1.0) * 32_767.0).astype("<i2").tobytes()


def smooth_pcm_tail(pcm16: bytes, sample_rate: int) -> bytes:
    """Fade the final PCM edge and add a short natural tail before playback ends."""
    samples = np.frombuffer(pcm16, dtype="<i2").astype(np.float32)
    fade_samples = min(len(samples), round(sample_rate * PCM_TAIL_FADE_MS / 1000))
    if fade_samples:
        samples[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples, endpoint=True)
    silence = np.zeros(round(sample_rate * PCM_TAIL_SILENCE_MS / 1000), dtype="<i2")
    return np.concatenate((np.rint(samples).astype("<i2"), silence)).tobytes()


def generate_wav(model: Any, text: str) -> tuple[bytes, int, int]:
    with torch.inference_mode():
        wavs, sample_rate = model.generate_custom_voice(
            text=text,
            language="Korean",
            speaker=TTS_SPEAKER,
            instruct=TTS_INSTRUCT,
            do_sample=True,
            max_new_tokens=512,
        )

    waveform = np.asarray(wavs[0], dtype=np.float32)
    duration_ms = round(len(waveform) / sample_rate * 1000)

    wav_buffer = io.BytesIO()
    sf.write(wav_buffer, waveform, sample_rate, format="WAV", subtype="PCM_16")

    return wav_buffer.getvalue(), sample_rate, duration_ms


def warmup_model(model: Any) -> None:
    generator: Any = None
    try:
        model.warmup(prefill_len=100)
        generator = model.generate_custom_voice_streaming(
            text="준비합니다.",
            speaker=TTS_SPEAKER,
            language="Korean",
            instruct=TTS_INSTRUCT,
            non_streaming_mode=True,
            do_sample=True,
            max_new_tokens=6,
            chunk_size=6,
        )
        for _ in generator:
            pass
    finally:
        close = getattr(generator, "close", None)
        if callable(close):
            close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not MODEL_PATH:
        raise RuntimeError("TTS_WORKER_MODEL_PATH 환경변수가 필요합니다.")

    model_path = Path(MODEL_PATH)

    if not model_path.is_dir():
        raise RuntimeError(f"모델 경로를 찾을 수 없습니다: {model_path}")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU를 찾을 수 없습니다.")

    compute_dtype = (
        torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    )

    app.state.model = FasterQwen3TTS.from_pretrained(
        str(model_path),
        device="cuda:0",
        dtype=compute_dtype,
        attn_implementation="sdpa",
        max_seq_len=2048,
        local_files_only=True,
    )
    if TTS_SPEAKER not in app.state.model.model.get_supported_speakers():
        raise RuntimeError(f"지원하지 않는 화자입니다: {TTS_SPEAKER}")
    app.state.model.predictor_graph.do_sample = True
    await asyncio.to_thread(warmup_model, app.state.model)
    app.state.generation_lock = asyncio.Lock()
    app.state.audio_cache: OrderedDict[str, tuple[bytes, int, int]] = OrderedDict()

    yield

    del app.state.model
    torch.cuda.empty_cache()


app = FastAPI(title="말해봄 TTS Worker", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/tts", response_class=Response)
async def synthesize(payload: TtsRequest) -> Response:
    question = normalize_question(payload.question)

    try:
        cached_audio = app.state.audio_cache.get(question)
        if cached_audio is None:
            async with app.state.generation_lock:
                cached_audio = app.state.audio_cache.get(question)
                if cached_audio is None:
                    cached_audio = await asyncio.to_thread(
                        generate_wav,
                        app.state.model,
                        question,
                    )
                    cache_audio(question, cached_audio)
                else:
                    app.state.audio_cache.move_to_end(question)
        else:
            app.state.audio_cache.move_to_end(question)
        wav_bytes, sample_rate, duration_ms = cached_audio
    except Exception:
        logger.exception("TTS synthesis failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS 생성에 실패했습니다.",
        )

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Audio-Sample-Rate": str(sample_rate),
            "X-Audio-Duration-Ms": str(duration_ms),
        },
    )


@app.post("/internal/tts/stream")
async def synthesize_stream(payload: TtsRequest) -> StreamingResponse:
    text = normalize_question(payload.question)

    async def events():
        request_started_at = time.perf_counter()
        try:
            async with app.state.generation_lock:
                for index, sentence in enumerate(split_sentences(text)):
                    chunk_started_at = time.perf_counter()
                    cached_audio = app.state.audio_cache.get(sentence)
                    cache_hit = cached_audio is not None
                    if cached_audio is None:
                        cached_audio = await asyncio.to_thread(
                            generate_wav,
                            app.state.model,
                            sentence,
                        )
                        cache_audio(sentence, cached_audio)
                    else:
                        app.state.audio_cache.move_to_end(sentence)

                    wav_bytes, sample_rate, duration_ms = cached_audio
                    logger.info(
                        "TTS stream chunk ready: index=%d chars=%d cache_hit=%s chunk_ms=%d elapsed_ms=%d",
                        index,
                        len(sentence),
                        cache_hit,
                        round((time.perf_counter() - chunk_started_at) * 1000),
                        round((time.perf_counter() - request_started_at) * 1000),
                    )
                    yield (json.dumps({
                        "type": "audio",
                        "index": index,
                        "audioBase64": base64.b64encode(wav_bytes).decode("ascii"),
                        "sampleRate": sample_rate,
                        "durationMs": duration_ms,
                    }) + "\n").encode("utf-8")
            logger.info(
                "TTS stream complete: sentence_count=%d elapsed_ms=%d",
                len(split_sentences(text)),
                round((time.perf_counter() - request_started_at) * 1000),
            )
            yield b'{"type":"complete"}\n'
        except Exception:
            logger.exception("Streaming TTS synthesis failed")
            yield '{"type":"error","message":"TTS 생성에 실패했습니다."}\n'.encode("utf-8")

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/internal/tts/pcm-stream")
async def synthesize_pcm_stream(payload: TtsRequest, request: Request) -> StreamingResponse:
    text = normalize_question(payload.question)

    async def events():
        started_at = time.perf_counter()
        sequence = 0
        generator: Any = None
        pending: tuple[Any, int] | None = None
        try:
            yield (json.dumps({
                "type": "start",
                "text": text,
                "format": "pcm_s16le",
                "sampleRate": 24_000,
                "channels": 1,
            }) + "\n").encode("utf-8")
            if await request.is_disconnected():
                return
            async with app.state.generation_lock:
                generator = app.state.model.generate_custom_voice_streaming(
                    text=text,
                    speaker=TTS_SPEAKER,
                    language="Korean",
                    instruct=TTS_INSTRUCT,
                    non_streaming_mode=True,
                    do_sample=True,
                    max_new_tokens=512,
                    chunk_size=6,
                )
                while True:
                    if await request.is_disconnected():
                        return
                    next_chunk = await asyncio.to_thread(next_stream_chunk, generator)
                    if next_chunk is None:
                        break
                    waveform, sample_rate, _timing = next_chunk
                    if pending is None:
                        pending = waveform, sample_rate
                        continue

                    pcm16 = waveform_to_pcm16(*pending)

                    logger.info(
                        "TTS PCM stream chunk ready: sequence=%d elapsed_ms=%d",
                        sequence,
                        round((time.perf_counter() - started_at) * 1000),
                    )
                    yield (json.dumps({
                        "type": "audio",
                        "sequence": sequence,
                        "pcmBase64": base64.b64encode(pcm16).decode("ascii"),
                    }) + "\n").encode("utf-8")
                    sequence += 1
                    pending = waveform, sample_rate

                if pending is not None:
                    pcm16 = smooth_pcm_tail(waveform_to_pcm16(*pending), 24_000)
                    logger.info(
                        "TTS PCM stream chunk ready: sequence=%d elapsed_ms=%d",
                        sequence,
                        round((time.perf_counter() - started_at) * 1000),
                    )
                    yield (json.dumps({
                        "type": "audio",
                        "sequence": sequence,
                        "pcmBase64": base64.b64encode(pcm16).decode("ascii"),
                    }) + "\n").encode("utf-8")
                    sequence += 1
            if sequence == 0:
                raise RuntimeError("생성된 PCM 청크가 없습니다.")
            logger.info(
                "TTS PCM stream complete: chunk_count=%d elapsed_ms=%d",
                sequence,
                round((time.perf_counter() - started_at) * 1000),
            )
            yield b'{"type":"complete"}\n'
        except Exception:
            logger.exception("PCM streaming TTS synthesis failed")
            yield '{"type":"error","code":"TTS_GENERATION_FAILED","message":"말하기 예시 음성을 만들지 못했습니다."}\n'.encode("utf-8")
        finally:
            close = getattr(generator, "close", None)
            if callable(close):
                close()

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
