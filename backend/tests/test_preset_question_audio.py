from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.supabase_settings import SupabaseSettings
from app.services.preset_question_audio import (
    LocalPresetQuestionAudioRepository,
    PresetQuestionAudioService,
    PresetQuestionAudioUnavailable,
    SupabasePresetQuestionAudioRepository,
)


SETTINGS = SupabaseSettings(
    url="https://project.supabase.co",
    publishable_key="publishable-key",
    service_role_key="service-role-key",
)


class FakeResponse:
    def __init__(self, status_code: int, content: bytes = b"") -> None:
        self.status_code = status_code
        self.content = content


class FakeHttpClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


class FakeSelector:
    def __init__(self, selected: dict[str, object] | None) -> None:
        self.selected = selected
        self.question_ids: list[str] = []

    def select_preset_question(self, question_id: str) -> dict[str, object] | None:
        self.question_ids.append(question_id)
        return self.selected


class PresetQuestionAudioTest(unittest.TestCase):
    def test_local_repository_reads_only_expected_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questioner-preset-01-v1.wav"
            path.write_bytes(b"RIFFlocal-wav")
            repository = LocalPresetQuestionAudioRepository(Path(directory))

            self.assertEqual(repository.read_wav("questioner-preset-01-v1"), b"RIFFlocal-wav")
            with self.assertRaises(KeyError):
                repository.read_wav("questioner-preset-11-v1")

    def test_repository_reads_only_expected_private_object_with_service_role(self):
        content = b"RIFFvalid-wav"
        http = FakeHttpClient([FakeResponse(200, content)])
        repository = SupabasePresetQuestionAudioRepository(SETTINGS, http)

        self.assertEqual(repository.read_wav("questioner-preset-01-v1"), content)

        request = http.requests[0]
        self.assertEqual(request["method"], "GET")
        self.assertEqual(
            request["url"],
            "https://project.supabase.co/storage/v1/object/preset-question-audio/questioner/questioner-preset-01-v1.wav",
        )
        self.assertEqual(request["headers"], {
            "apikey": "service-role-key",
            "Authorization": "Bearer service-role-key",
        })

    def test_invalid_asset_id_is_rejected_before_storage_request(self):
        http = FakeHttpClient([])
        repository = SupabasePresetQuestionAudioRepository(SETTINGS, http)

        with self.assertRaises(KeyError):
            repository.read_wav("unexpected-asset")

        self.assertEqual(http.requests, [])

    def test_storage_error_does_not_return_audio(self):
        repository = SupabasePresetQuestionAudioRepository(SETTINGS, FakeHttpClient([FakeResponse(500)]))

        with self.assertRaises(PresetQuestionAudioUnavailable):
            repository.read_wav("questioner-preset-01-v1")

    def test_service_rejects_draft_or_unknown_question_before_storage_read(self):
        selector = FakeSelector(None)
        repository = SupabasePresetQuestionAudioRepository(SETTINGS, FakeHttpClient([]))
        service = PresetQuestionAudioService(selector, repository)

        with self.assertRaises(KeyError):
            service.read_wav("preset-11")

        self.assertEqual(selector.question_ids, ["preset-11"])
