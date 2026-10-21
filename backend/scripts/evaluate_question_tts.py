from __future__ import annotations

import argparse
import io
import json
import sys
import threading
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.question_tts_settings import QuestionTtsSettings
from app.services.question_tts import QuestionTtsUnavailableError, prepare_synthesis_text, validate_question_wav
from app.services.question_tts_stream import (
    CHANNELS,
    QUIET_RMS_DB,
    QUIET_TAIL_SECONDS,
    SAMPLE_RATE,
    GeneratedQuestionPcm,
    pcm16_rms_db,
)
from app.services.qwen_question_tts import QwenQuestionTtsSynthesizer


EVALUATION_REQUESTS = (
    ("preset-01", "자기소개를 간단히 말씀해 주세요."),
    ("preset-02", "지원한 직무에 관심을 갖게 된 계기를 말씀해 주세요."),
    ("preset-03", "협업 과정에서 갈등을 해결한 경험을 말씀해 주세요."),
    ("preset-04", "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?"),
    ("preset-05", "본인의 강점과 보완할 점을 말씀해 주세요."),
    ("preset-06", "목표를 세우고 끝까지 완수한 경험이 있나요?"),
    ("preset-07", "새로운 환경에 적응했던 경험을 말씀해 주세요."),
    ("preset-08", "피드백을 받아 개선한 경험을 말씀해 주세요."),
    ("preset-09", "우리 회사와 직무를 선택한 이유는 무엇인가요?"),
    ("preset-10", "입사 후 이루고 싶은 목표를 말씀해 주세요."),
    ("custom-01", "프로젝트에서 맡았던 역할과 기여를 구체적으로 설명해 주세요."),
    ("custom-02", "예상하지 못한 문제 상황에서 우선순위를 정한 기준을 말씀해 주세요."),
    ("custom-03", "팀의 성과를 높이기 위해 제안하거나 실행한 일이 있다면 말씀해 주세요."),
)


def run_stream_evaluation(
    synthesizer: Any,
    output_dir: Path,
    *,
    gpu_peak_bytes: Callable[[], int],
) -> list[dict[str, object]]:
    if output_dir.exists():
        raise FileExistsError(f"Evaluation output already exists: {output_dir.name}")
    wav_dir = output_dir / "wavs"
    wav_dir.mkdir(parents=True)
    records: list[dict[str, object]] = []

    for request_id, text in EVALUATION_REQUESTS:
        started_at = time.perf_counter()
        first_audio_seconds: float | None = None
        try:
            pcm16, stop_reason, first_audio_seconds = _collect_stream(
                synthesizer,
                prepare_synthesis_text(text),
                started_at,
            )
            duration_ms = round(len(pcm16) / (SAMPLE_RATE * 2) * 1000)
            wav_bytes = _pcm16_to_wav(pcm16)
            validate_question_wav(wav_bytes, duration_ms)
            (wav_dir / f"{request_id}.wav").write_bytes(wav_bytes)
            generation_seconds = time.perf_counter() - started_at
            audio_duration_seconds = duration_ms / 1000
            record: dict[str, object] = {
                "requestId": request_id,
                "firstAudioSeconds": round(first_audio_seconds, 4),
                "generationSeconds": round(generation_seconds, 4),
                "audioDurationSeconds": audio_duration_seconds,
                "rtf": round(generation_seconds / audio_duration_seconds, 4),
                "gpuPeakAllocatedBytes": gpu_peak_bytes(),
                "stopReason": stop_reason,
                "wavFormatValid": True,
                "manualReview": "pending",
            }
        except (QuestionTtsUnavailableError, OSError, ValueError):
            record = {
                "requestId": request_id,
                "firstAudioSeconds": first_audio_seconds,
                "generationSeconds": round(time.perf_counter() - started_at, 4),
                "audioDurationSeconds": None,
                "rtf": None,
                "gpuPeakAllocatedBytes": gpu_peak_bytes(),
                "stopReason": "failed",
                "wavFormatValid": False,
                "manualReview": "not_generated",
            }
        records.append(record)

    (output_dir / "metrics.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "requestCount": len(records),
                "generatedCount": sum(record["wavFormatValid"] is True for record in records),
                "manualReview": "pending",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return records


def _collect_stream(
    synthesizer: Any,
    synthesis_text: str,
    started_at: float,
) -> tuple[bytes, str, float]:
    cancel = threading.Event()
    generator = synthesizer.stream(synthesis_text, cancel)
    chunks: list[bytes] = []
    saw_active_audio = False
    quiet_seconds = 0.0
    stopped_by_quiet_tail = False
    final_chunk_received = False
    first_audio_seconds: float | None = None
    try:
        for chunk in generator:
            _validate_chunk(chunk)
            if first_audio_seconds is None:
                first_audio_seconds = time.perf_counter() - started_at
            chunks.append(chunk.pcm16)
            final_chunk_received = chunk.is_final
            if pcm16_rms_db(chunk.pcm16) > QUIET_RMS_DB:
                saw_active_audio = True
                quiet_seconds = 0.0
            elif saw_active_audio:
                quiet_seconds += len(chunk.pcm16) / (SAMPLE_RATE * 2)
                if quiet_seconds >= QUIET_TAIL_SECONDS:
                    stopped_by_quiet_tail = True
                    _close_generator(generator)
                    break
    finally:
        cancel.set()

    if not chunks or first_audio_seconds is None:
        raise QuestionTtsUnavailableError()
    if not stopped_by_quiet_tail and not final_chunk_received:
        raise QuestionTtsUnavailableError()
    return b"".join(chunks), "energy_tail_gate" if stopped_by_quiet_tail else "model_eos", first_audio_seconds


def _validate_chunk(chunk: GeneratedQuestionPcm) -> None:
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


def _close_generator(generator: Any) -> None:
    close = getattr(generator, "close", None)
    if callable(close):
        close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local-only question TTS stream listening evaluation.")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or Path("local-results") / f"question-tts-stream-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    try:
        synthesizer = QwenQuestionTtsSynthesizer.from_settings(QuestionTtsSettings.from_env())
        synthesizer.warmup()
        records = run_stream_evaluation(synthesizer, output_dir, gpu_peak_bytes=_gpu_peak_bytes)
    except (FileExistsError, QuestionTtsUnavailableError, OSError):
        print("question tts stream evaluation unavailable")
        return 1
    failed = sum(record["wavFormatValid"] is not True for record in records)
    print(f"question tts stream evaluation completed: requests={len(records)}, failed={failed}")
    return 0 if failed == 0 else 1


def _gpu_peak_bytes() -> int:
    import torch

    return int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0


if __name__ == "__main__":
    raise SystemExit(main())
