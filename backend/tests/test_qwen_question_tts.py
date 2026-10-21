from __future__ import annotations

import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.question_tts_settings import QuestionTtsSettings
from app.services.question_tts import QuestionTtsUnavailableError, validate_question_wav
from app.services.qwen_question_tts import QUESTIONER_SPEAKER, QwenQuestionTtsSynthesizer


class TrackedRuntimeGenerator:
    def __init__(self, runtime: "FakeFasterRuntime") -> None:
        self.runtime = runtime
        self.index = 0

    def __iter__(self) -> "TrackedRuntimeGenerator":
        return self

    def __next__(self) -> tuple[np.ndarray, int, dict[str, object]]:
        if self.index >= len(self.runtime.chunks):
            raise StopIteration
        chunk = self.runtime.chunks[self.index]
        self.index += 1
        total_steps = (
            self.runtime.last_total_steps
            if self.index == len(self.runtime.chunks) and self.runtime.last_total_steps is not None
            else self.index
        )
        return chunk, self.runtime.sample_rate, {
            "is_final": self.runtime.final_chunk and self.index == len(self.runtime.chunks),
            "total_steps_so_far": total_steps,
        }

    def close(self) -> None:
        self.runtime.runtime_generator_closed = True


class FakeFasterRuntime:
    def __init__(
        self,
        speakers: list[str],
        chunks: list[np.ndarray] | None = None,
        sample_rate: int = 24_000,
        final_chunk: bool = True,
        last_total_steps: int | None = None,
    ) -> None:
        self.speakers = speakers
        self.chunks = chunks if chunks is not None else [np.zeros(480, dtype=np.float32)]
        self.sample_rate = sample_rate
        self.final_chunk = final_chunk
        self.last_total_steps = last_total_steps
        self.streaming_calls: list[dict[str, object]] = []
        self.warmup_calls: list[int] = []
        self.model = SimpleNamespace(get_supported_speakers=lambda: self.speakers)
        self.predictor_graph = SimpleNamespace(do_sample=True)
        self.runtime_generator_closed = False
        self.last_runtime_generator: TrackedRuntimeGenerator | None = None

    def warmup(self, *, prefill_len: int) -> None:
        self.warmup_calls.append(prefill_len)

    def generate_custom_voice_streaming(self, **kwargs: object):
        self.streaming_calls.append(kwargs)
        self.last_runtime_generator = TrackedRuntimeGenerator(self)
        return self.last_runtime_generator


def make_synthesizer(
    runtime: FakeFasterRuntime,
    cuda_available=lambda: True,
) -> tuple[QwenQuestionTtsSynthesizer, list[tuple[str, dict[str, object]]]]:
    loader_calls: list[tuple[str, dict[str, object]]] = []

    def model_loader(path: str, **kwargs: object) -> FakeFasterRuntime:
        loader_calls.append((path, kwargs))
        return runtime

    settings = QuestionTtsSettings(Path("local-model"))
    return (
        QwenQuestionTtsSynthesizer.from_settings(
            settings,
            model_loader=model_loader,
            cuda_available=cuda_available,
            bfloat16="bf16",
        ),
        loader_calls,
    )


class QuestionTtsSettingsTest(unittest.TestCase):
    def test_from_env_requires_an_existing_local_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.dict(os.environ, {"QUESTION_TTS_MODEL_PATH": temporary_directory}, clear=False):
                self.assertEqual(QuestionTtsSettings.from_env().model_path, Path(temporary_directory))

        with patch.dict(os.environ, {"QUESTION_TTS_MODEL_PATH": ""}, clear=False):
            with self.assertRaises(QuestionTtsUnavailableError):
                QuestionTtsSettings.from_env()


class QwenQuestionTtsSynthesizerTest(unittest.TestCase):
    def test_loads_faster_runtime_once_from_local_candidate04_cuda_path(self) -> None:
        synthesizer, loader_calls = make_synthesizer(FakeFasterRuntime([QUESTIONER_SPEAKER]))

        self.assertIsInstance(synthesizer, QwenQuestionTtsSynthesizer)
        self.assertEqual(loader_calls, [("local-model", {
            "device": "cuda:0",
            "dtype": "bf16",
            "attn_implementation": "sdpa",
            "max_seq_len": 2048,
            "local_files_only": True,
        })])
        self.assertFalse(synthesizer.model.predictor_graph.do_sample)

    def test_warmup_uses_non_user_bounded_primer_once(self) -> None:
        runtime = FakeFasterRuntime([QUESTIONER_SPEAKER])
        synthesizer, _ = make_synthesizer(runtime)

        synthesizer.warmup()
        synthesizer.warmup()

        self.assertEqual(runtime.warmup_calls, [100])
        self.assertEqual(len(runtime.streaming_calls), 1)
        self.assertEqual(runtime.streaming_calls[0]["text"], "준비합니다.//")
        self.assertEqual(runtime.streaming_calls[0]["max_new_tokens"], 6)
        self.assertEqual(runtime.streaming_calls[0]["chunk_size"], 6)
        self.assertFalse(runtime.streaming_calls[0]["do_sample"])

    def test_stream_converts_runtime_chunks_to_pcm16_and_fallback_uses_same_suffix(self) -> None:
        runtime = FakeFasterRuntime([QUESTIONER_SPEAKER])
        synthesizer, _ = make_synthesizer(runtime)

        chunks = list(synthesizer.stream("질문입니다.//", threading.Event()))
        audio = synthesizer.synthesize("질문입니다.")

        self.assertEqual(runtime.streaming_calls[0]["text"], "질문입니다.//")
        self.assertEqual(chunks[0].sample_rate, 24_000)
        self.assertEqual(chunks[0].channels, 1)
        self.assertTrue(chunks[0].is_final)
        self.assertEqual(len(chunks[0].pcm16), 960)
        self.assertEqual(runtime.streaming_calls[-1]["text"], "질문입니다.//")
        validate_question_wav(audio.wav_bytes, audio.duration_ms)

    def test_rejects_unavailable_cuda_unknown_speaker_or_malformed_runtime_output(self) -> None:
        with self.assertRaises(QuestionTtsUnavailableError):
            make_synthesizer(FakeFasterRuntime([QUESTIONER_SPEAKER]), cuda_available=lambda: False)

        with self.assertRaises(QuestionTtsUnavailableError):
            make_synthesizer(FakeFasterRuntime(["other"]))

        for runtime in (
            FakeFasterRuntime([QUESTIONER_SPEAKER], [np.array([np.nan], dtype=np.float32)]),
            FakeFasterRuntime([QUESTIONER_SPEAKER], [np.zeros((2, 480), dtype=np.float32)]),
            FakeFasterRuntime([QUESTIONER_SPEAKER], sample_rate=16_000),
        ):
            synthesizer, _ = make_synthesizer(runtime)
            with self.assertRaises(QuestionTtsUnavailableError):
                list(synthesizer.stream("질문입니다.//", threading.Event()))

    def test_fallback_rejects_a_stream_without_a_final_termination_signal(self) -> None:
        synthesizer, _ = make_synthesizer(
            FakeFasterRuntime([QUESTIONER_SPEAKER], last_total_steps=512)
        )

        with self.assertRaises(QuestionTtsUnavailableError):
            synthesizer.synthesize("질문입니다.")

    def test_stream_marks_an_exact_chunk_boundary_as_final_only_after_runtime_exhaustion(self) -> None:
        synthesizer, _ = make_synthesizer(
            FakeFasterRuntime([QUESTIONER_SPEAKER], final_chunk=False, last_total_steps=6)
        )

        chunks = list(synthesizer.stream("질문입니다.//", threading.Event()))

        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].is_final)

    def test_closing_outer_stream_closes_the_runtime_generator_without_cancellation(self) -> None:
        runtime = FakeFasterRuntime([QUESTIONER_SPEAKER], [np.zeros(480, dtype=np.float32)] * 2)
        synthesizer, _ = make_synthesizer(runtime)

        stream = synthesizer.stream("질문입니다.//", threading.Event())
        next(stream)
        stream.close()

        self.assertTrue(runtime.runtime_generator_closed)


if __name__ == "__main__":
    unittest.main()
