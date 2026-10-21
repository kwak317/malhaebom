from __future__ import annotations

import io
import sys
import unittest
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.question_tts import (
    GeneratedQuestionAudio,
    QuestionTtsInputError,
    QuestionTtsService,
    QuestionTtsUnavailableError,
    normalize_question,
    prepare_synthesis_text,
    validate_question_wav,
)
from app.services.question_tts_persistence import QuestionTtsRecord


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    access_token: str


USER = AuthenticatedUser("user-1", "user-access-token")
RECORD = QuestionTtsRecord(
    audio_id="audio-1",
    user_id="user-1",
    audio_path="user-1/audio-1/question.wav",
    duration_ms=1000,
    expires_at=datetime(2026, 8, 20, tzinfo=UTC),
)


def wav_bytes(sample_rate: int = 24_000, frames: int = 24_000) -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"\x00\x00" * frames)
    return stream.getvalue()


class FakeSynthesizer:
    def __init__(self, result: GeneratedQuestionAudio | Exception) -> None:
        self.result = result
        self.calls: list[str] = []

    def synthesize(self, question: str) -> GeneratedQuestionAudio:
        self.calls.append(question)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeRepository:
    def __init__(self) -> None:
        self.created: list[tuple[AuthenticatedUser, GeneratedQuestionAudio]] = []
        self.wav = wav_bytes()

    def create(self, user: AuthenticatedUser, audio: GeneratedQuestionAudio) -> QuestionTtsRecord:
        self.created.append((user, audio))
        return RECORD

    def read_wav(self, user: AuthenticatedUser, audio_id: str, now: datetime) -> bytes:
        return self.wav


class NormalizeQuestionTest(unittest.TestCase):
    def test_prepare_synthesis_text_adds_exact_suffix_without_space(self) -> None:
        self.assertEqual(prepare_synthesis_text("질문입니다."), "질문입니다.//")

    def test_trims_outer_space_and_counts_only_non_whitespace_characters(self) -> None:
        self.assertEqual(normalize_question("  협업  경험을  말해 주세요.  "), "협업  경험을  말해 주세요.")
        self.assertEqual(normalize_question(("가 " * 200).strip()), ("가 " * 200).strip())

    def test_rejects_blank_or_more_than_200_non_whitespace_characters(self) -> None:
        for value in (" \t ", "가" * 201):
            with self.assertRaises(QuestionTtsInputError) as raised:
                normalize_question(value)
            self.assertEqual(raised.exception.message, "질문은 공백 제외 1자 이상 200자 이하로 입력해 주세요.")

    def test_rejects_html_control_and_null_characters(self) -> None:
        for value in ("<script>x</script>", "안녕\x00하세요", "안녕\x07하세요"):
            with self.assertRaises(QuestionTtsInputError):
                normalize_question(value)


class QuestionTtsServiceTest(unittest.TestCase):
    def test_invalid_question_never_calls_model_or_persistence(self) -> None:
        synthesizer = FakeSynthesizer(GeneratedQuestionAudio(wav_bytes(), 1000))
        repository = FakeRepository()
        service = QuestionTtsService(synthesizer, repository)

        for value in (" ", "가" * 201, "<b>질문</b>", "질문\x00"):
            with self.assertRaises(QuestionTtsInputError):
                service.create(USER, value)

        self.assertEqual(synthesizer.calls, [])
        self.assertEqual(repository.created, [])

    def test_bad_wav_duration_or_model_failure_creates_no_storage_row(self) -> None:
        for result in (
            GeneratedQuestionAudio(b"not-a-wav", 1000),
            GeneratedQuestionAudio(wav_bytes(), 1200),
            RuntimeError("model failed"),
        ):
            synthesizer = FakeSynthesizer(result)
            repository = FakeRepository()
            with self.assertRaises(QuestionTtsUnavailableError):
                QuestionTtsService(synthesizer, repository).create(USER, "질문입니다.")
            self.assertEqual(repository.created, [])

    def test_valid_audio_is_persisted_after_synthesis_and_returns_normalized_text(self) -> None:
        audio = GeneratedQuestionAudio(wav_bytes(), 1000)
        synthesizer = FakeSynthesizer(audio)
        repository = FakeRepository()

        created = QuestionTtsService(synthesizer, repository).create(USER, "  협업 경험을 말해 주세요. ")

        self.assertEqual(synthesizer.calls, ["협업 경험을 말해 주세요."])
        self.assertEqual(repository.created, [(USER, audio)])
        self.assertEqual(created.record, RECORD)
        self.assertEqual(created.text, "협업 경험을 말해 주세요.")


class ValidateQuestionWavTest(unittest.TestCase):
    def test_accepts_only_nonempty_24khz_mono_pcm16_wav_with_matching_duration(self) -> None:
        validate_question_wav(wav_bytes(), 1000)
        for content, duration_ms in ((b"not-a-wav", 1000), (wav_bytes(sample_rate=16_000), 1000), (wav_bytes(frames=0), 0), (wav_bytes(), 1200)):
            with self.assertRaises(QuestionTtsUnavailableError):
                validate_question_wav(content, duration_ms)


if __name__ == "__main__":
    unittest.main()
