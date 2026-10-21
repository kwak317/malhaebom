from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app
from app.services.preset_question_audio import PresetQuestionAudioUnavailable


class FakePresetAudioService:
    def __init__(self, content: bytes | None = None, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[str] = []

    def read_wav(self, question_id: str) -> bytes:
        self.calls.append(question_id)
        if self.error is not None:
            raise self.error
        return self.content or b""


class PresetQuestionAudioApiTest(unittest.TestCase):
    def test_anonymous_accepted_preset_returns_wav(self):
        service = FakePresetAudioService(content=b"RIFFvalid-wav")
        client = TestClient(create_app(preset_question_audio_service=service))

        response = client.get("/api/preset-questions/preset-01/audio")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.headers["cache-control"], "public, max-age=300")
        self.assertEqual(response.content, b"RIFFvalid-wav")
        self.assertEqual(service.calls, ["preset-01"])

    def test_unknown_or_unaccepted_preset_returns_404_without_audio_fallback(self):
        service = FakePresetAudioService(error=KeyError("preset-11"))
        client = TestClient(create_app(preset_question_audio_service=service))

        response = client.get("/api/preset-questions/preset-11/audio")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "질문 음성을 찾을 수 없습니다.")
        self.assertEqual(service.calls, ["preset-11"])

    def test_storage_failure_returns_503_without_internal_detail(self):
        service = FakePresetAudioService(error=PresetQuestionAudioUnavailable())
        client = TestClient(create_app(preset_question_audio_service=service))

        response = client.get("/api/preset-questions/preset-01/audio")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "질문 음성을 준비하지 못했습니다. 다시 시도해 주세요.")
