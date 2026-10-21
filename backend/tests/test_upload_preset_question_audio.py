from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.supabase_settings import SupabaseSettings
from scripts.upload_preset_question_audio import (
    PresetQuestionUploader,
    UploadError,
    UploadValidationError,
)


SETTINGS = SupabaseSettings(
    url="https://project.supabase.co",
    publishable_key="publishable-key",
    service_role_key="service-role-key",
)


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class FakeHttpClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


def write_pcm16_wav(path: Path, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"\x00\x00" * sample_rate)


class UploadPresetQuestionAudioTest(unittest.TestCase):
    def test_invalid_wav_stops_before_any_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory)
            write_pcm16_wav(source_dir / "question_01.wav", 16_000)
            http = FakeHttpClient([])
            uploader = PresetQuestionUploader(SETTINGS, http)

            with self.assertRaises(UploadValidationError):
                uploader.upload_source_directory(source_dir)

        self.assertEqual(http.requests, [])

    def test_second_upload_failure_deletes_first_uploaded_object(self):
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory)
            for number in range(1, 11):
                write_pcm16_wav(source_dir / f"question_{number:02d}.wav", 24_000)
            http = FakeHttpClient([FakeResponse(201), FakeResponse(500), FakeResponse(200)])
            uploader = PresetQuestionUploader(SETTINGS, http)

            with self.assertRaises(UploadError):
                uploader.upload_source_directory(source_dir)

        self.assertEqual([request["method"] for request in http.requests], ["POST", "POST", "DELETE"])
        self.assertEqual(http.requests[0]["headers"], {
            "apikey": "service-role-key",
            "Authorization": "Bearer service-role-key",
            "Content-Type": "audio/wav",
            "x-upsert": "false",
        })
