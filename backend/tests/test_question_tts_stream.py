from __future__ import annotations

import math
import struct
import sys
import threading
import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.question_tts_persistence import QuestionTtsRecord
from app.services.question_tts_persistence import QuestionTtsPersistenceError
from app.services.question_tts_stream import (
    GeneratedQuestionPcm,
    QuestionTtsStreamService,
    StreamAudio,
    StreamComplete,
    StreamError,
    StreamStart,
)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    access_token: str


USER = AuthenticatedUser("user-1", "test-access-token")
RECORD = QuestionTtsRecord(
    audio_id="audio-1",
    user_id="user-1",
    audio_path="user-1/audio-1/question.wav",
    duration_ms=1,
    expires_at=datetime(2026, 8, 20, tzinfo=UTC),
)


def pcm_at_db(seconds: float, db: float) -> bytes:
    frames = round(24_000 * seconds)
    amplitude = round(32_767 * math.pow(10.0, db / 20.0))
    return struct.pack(f"<{frames}h", *([amplitude] * frames))


def active_pcm() -> GeneratedQuestionPcm:
    return GeneratedQuestionPcm(pcm16=pcm_at_db(0.12, -20.0))


def quiet_pcm(seconds: float) -> GeneratedQuestionPcm:
    return GeneratedQuestionPcm(pcm16=pcm_at_db(seconds, -50.0))


class ClosableChunks:
    def __init__(
        self,
        chunks: list[GeneratedQuestionPcm],
        cancel_after_first: threading.Event | None = None,
    ) -> None:
        self.chunks = chunks
        self.cancel_after_first = cancel_after_first
        self.index = 0
        self.closed = False

    def __iter__(self) -> "ClosableChunks":
        return self

    def __next__(self) -> GeneratedQuestionPcm:
        if self.index >= len(self.chunks):
            raise StopIteration
        chunk = self.chunks[self.index]
        self.index += 1
        if self.index == 1 and self.cancel_after_first is not None:
            self.cancel_after_first.set()
        return chunk

    def close(self) -> None:
        self.closed = True


class FakeStreamSynthesizer:
    def __init__(
        self,
        chunks: list[GeneratedQuestionPcm],
        cancel_after_first: threading.Event | None = None,
    ) -> None:
        self.chunks = ClosableChunks(chunks, cancel_after_first)
        self.calls: list[str] = []

    def stream(self, synthesis_text: str, cancel: threading.Event) -> ClosableChunks:
        self.calls.append(synthesis_text)
        return self.chunks


class FakeRepository:
    def __init__(self) -> None:
        self.created: list[object] = []

    def create(self, user: AuthenticatedUser, audio: object) -> QuestionTtsRecord:
        self.created.append(audio)
        return RECORD


class FailingRepository(FakeRepository):
    def create(self, user: AuthenticatedUser, audio: object) -> QuestionTtsRecord:
        self.created.append(audio)
        raise QuestionTtsPersistenceError("PERSISTENCE_FAILED", "failed")


class QuestionTtsStreamServiceTest(unittest.TestCase):
    def test_stream_sends_normalized_text_and_contiguous_audio_before_complete(self) -> None:
        synthesizer = FakeStreamSynthesizer([active_pcm(), quiet_pcm(0.5)])
        repository = FakeRepository()

        events = list(
            QuestionTtsStreamService(synthesizer, repository).events(
                USER, "  질문입니다.  ", threading.Event()
            )
        )

        self.assertEqual(
            [type(event) for event in events],
            [StreamStart, StreamAudio, StreamAudio, StreamComplete],
        )
        self.assertEqual(events[0].text, "질문입니다.")
        self.assertEqual(
            [event.sequence for event in events if isinstance(event, StreamAudio)], [0, 1]
        )
        self.assertEqual(synthesizer.calls, ["질문입니다.//"])
        self.assertEqual(len(repository.created), 1)

    def test_half_second_quiet_tail_after_speech_closes_generator_before_later_audio(self) -> None:
        synthesizer = FakeStreamSynthesizer(
            [active_pcm(), quiet_pcm(0.25), quiet_pcm(0.25), active_pcm()]
        )
        repository = FakeRepository()

        events = list(
            QuestionTtsStreamService(synthesizer, repository).events(
                USER, "질문입니다.", threading.Event()
            )
        )

        self.assertTrue(synthesizer.chunks.closed)
        self.assertEqual(len([event for event in events if isinstance(event, StreamAudio)]), 3)
        self.assertIsInstance(events[-1], StreamComplete)
        self.assertEqual(len(repository.created), 1)

    def test_cancel_closes_generator_without_persisting_partial_audio(self) -> None:
        cancel = threading.Event()
        synthesizer = FakeStreamSynthesizer(
            [active_pcm(), active_pcm()], cancel_after_first=cancel
        )
        repository = FakeRepository()

        events = list(
            QuestionTtsStreamService(synthesizer, repository).events(
                USER, "질문입니다.", cancel
            )
        )

        self.assertTrue(synthesizer.chunks.closed)
        self.assertFalse(any(isinstance(event, StreamComplete) for event in events))
        self.assertEqual(repository.created, [])

    def test_invalid_pcm_ends_with_safe_error_without_persisting(self) -> None:
        synthesizer = FakeStreamSynthesizer([GeneratedQuestionPcm(pcm16=b"\x00")])
        repository = FakeRepository()

        events = list(
            QuestionTtsStreamService(synthesizer, repository).events(
                USER, "질문입니다.", threading.Event()
            )
        )

        self.assertEqual([type(event) for event in events], [StreamStart, StreamError])
        self.assertEqual(events[-1].code, "TTS_GENERATION_FAILED")
        self.assertEqual(repository.created, [])

    def test_persistence_failure_ends_with_error_without_complete(self) -> None:
        synthesizer = FakeStreamSynthesizer([active_pcm()])
        repository = FailingRepository()

        events = list(
            QuestionTtsStreamService(synthesizer, repository).events(
                USER, "질문입니다.", threading.Event()
            )
        )

        self.assertEqual([type(event) for event in events], [StreamStart, StreamAudio, StreamError])
        self.assertEqual(events[-1].code, "TTS_GENERATION_FAILED")
        self.assertFalse(any(isinstance(event, StreamComplete) for event in events))

    def test_non_final_stream_exhaustion_does_not_persist_a_possibly_truncated_wav(self) -> None:
        synthesizer = FakeStreamSynthesizer([active_pcm()])
        repository = FakeRepository()

        events = list(
            QuestionTtsStreamService(synthesizer, repository).events(
                USER, "질문입니다.", threading.Event()
            )
        )

        self.assertEqual([type(event) for event in events], [StreamStart, StreamAudio, StreamError])
        self.assertEqual(repository.created, [])


if __name__ == "__main__":
    unittest.main()
