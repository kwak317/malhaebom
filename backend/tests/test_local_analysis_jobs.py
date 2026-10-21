from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.stt import FillerAnalysis, SttResult
from app.schemas.delivery import SpeechSegment
from app.services.delivery_analysis import DeliveryAnalyzer
from app.services.local_analysis_jobs import AudioValidationError, LocalAnalysisJobService


def wav_bytes(duration_seconds: float) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
        path = Path(temp.name)
    try:
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16_000)
            audio.writeframes(b"\x00\x00" * int(16_000 * duration_seconds))
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


class FakeTranscriber:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[Path, str]] = []

    def transcribe(self, audio_path: Path | str, source_id: str) -> SttResult:
        self.calls.append((Path(audio_path), source_id))
        if self.fail:
            raise RuntimeError("internal path must stay hidden")
        return SttResult(
            source_id=source_id,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            language="ko",
            language_probability=0.99,
            audio_duration_sec=6.0,
            processing_time_sec=0.2,
            rtf=0.0333,
            text="전사문",
            fillers=FillerAnalysis(counts={"음": 0, "어": 0}, total_count=0, occurrences={"음": [], "어": []}),
            segments=[],
            words=[],
        )


class FakeVadDetector:
    def __init__(self, segments: list[SpeechSegment] | None = None, fail: bool = False) -> None:
        self.segments = segments or []
        self.fail = fail
        self.calls: list[Path] = []

    def detect(self, audio_path: Path) -> list[SpeechSegment]:
        self.calls.append(audio_path)
        if self.fail:
            raise RuntimeError("local audio path must stay hidden")
        return self.segments


class LocalAnalysisJobServiceTest(unittest.TestCase):
    def test_valid_wav_completes_and_deletes_temp_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            transcriber = FakeTranscriber()
            detector = FakeVadDetector([SpeechSegment(start=0.0, end=3.0)])
            service = LocalAnalysisJobService(
                transcriber,
                Path(directory),
                vad_detector=detector,
                delivery_analyzer=DeliveryAnalyzer(),
            )
            job = service.create_job("attempt-123", "answer.wav", wav_bytes(6.0))
            saved_path = job.audio_path
            completed = service.process(job.job_id)

        self.assertEqual(completed.status, "completed")
        self.assertEqual(completed.result.source_id, "attempt-123")
        self.assertEqual(completed.delivery.metrics.speech_duration_sec, 3.0)
        self.assertEqual(transcriber.calls[0][1], "attempt-123")
        self.assertEqual(detector.calls, [saved_path])
        self.assertFalse(saved_path.exists())

    def test_empty_vad_result_returns_no_speech_error(self):
        with tempfile.TemporaryDirectory() as directory:
            service = LocalAnalysisJobService(
                FakeTranscriber(),
                Path(directory),
                vad_detector=FakeVadDetector(),
                delivery_analyzer=DeliveryAnalyzer(),
            )
            job = service.create_job("attempt-123", "answer.wav", wav_bytes(6.0))
            completed = service.process(job.job_id)

        self.assertEqual(completed.status, "failed")
        self.assertEqual(completed.error_code, "NO_SPEECH_DETECTED")
        self.assertIsNone(completed.result)
        self.assertIsNone(completed.delivery)

    def test_invalid_duration_does_not_call_transcriber(self):
        with tempfile.TemporaryDirectory() as directory:
            transcriber = FakeTranscriber()
            service = LocalAnalysisJobService(transcriber, Path(directory))
            with self.assertRaises(AudioValidationError) as error:
                service.create_job("attempt-123", "answer.wav", wav_bytes(4.0))

        self.assertEqual(error.exception.code, "INVALID_DURATION")
        self.assertEqual(transcriber.calls, [])

    def test_transcriber_failure_hides_local_path_and_deletes_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            service = LocalAnalysisJobService(
                FakeTranscriber(fail=True),
                Path(directory),
                vad_detector=FakeVadDetector([SpeechSegment(start=0.0, end=3.0)]),
            )
            job = service.create_job("attempt-123", "answer.wav", wav_bytes(6.0))
            saved_path = job.audio_path
            failed = service.process(job.job_id)

        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.error_code, "STT_FAILED")
        self.assertNotIn(str(saved_path), failed.error_message)
        self.assertFalse(saved_path.exists())

    def test_vad_failure_hides_transcript_and_local_path(self):
        with tempfile.TemporaryDirectory() as directory:
            service = LocalAnalysisJobService(
                FakeTranscriber(),
                Path(directory),
                vad_detector=FakeVadDetector(fail=True),
                delivery_analyzer=DeliveryAnalyzer(),
            )
            job = service.create_job("attempt-123", "answer.wav", wav_bytes(6.0))
            saved_path = job.audio_path
            failed = service.process(job.job_id)

        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.error_code, "ANALYSIS_FAILED")
        self.assertIsNone(failed.result)
        self.assertIsNone(failed.delivery)
        self.assertNotIn(str(saved_path), failed.error_message)
        self.assertFalse(saved_path.exists())

    def test_unknown_job_raises_key_error(self):
        service = LocalAnalysisJobService(FakeTranscriber())
        with self.assertRaises(KeyError):
            service.get("unknown")
