from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import httpx

from app.core.supabase_settings import SupabaseSettings
from app.services.tts_asset_selector import TtsAssetSelector


PRESET_QUESTION_BUCKET_ID = "preset-question-audio"
ASSET_ID_PATTERN = re.compile(r"^questioner-preset-(0[1-9]|10)-v1$")


class PresetQuestionAudioUnavailable(RuntimeError):
    pass


class LocalPresetQuestionAudioRepository:
    """Read pre-generated private WAV assets from a server-local directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def read_wav(self, audio_asset_id: str) -> bytes:
        if not ASSET_ID_PATTERN.fullmatch(audio_asset_id):
            raise KeyError(audio_asset_id)
        try:
            content = (self.directory / f"{audio_asset_id}.wav").read_bytes()
        except FileNotFoundError as error:
            raise KeyError(audio_asset_id) from error
        if not content:
            raise PresetQuestionAudioUnavailable()
        return content


class SupabasePresetQuestionAudioRepository:
    """Server-only reader for reviewed preset-question WAV objects."""

    def __init__(self, settings: SupabaseSettings, http_client: httpx.Client | Any | None = None) -> None:
        if not settings.service_role_key:
            raise PresetQuestionAudioUnavailable()
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def read_wav(self, audio_asset_id: str) -> bytes:
        if not ASSET_ID_PATTERN.fullmatch(audio_asset_id):
            raise KeyError(audio_asset_id)

        try:
            response = self.http.request(
                "GET",
                f"{self.settings.url}/storage/v1/object/{PRESET_QUESTION_BUCKET_ID}/questioner/{audio_asset_id}.wav",
                headers={
                    "apikey": self.settings.service_role_key or "",
                    "Authorization": f"Bearer {self.settings.service_role_key}",
                },
            )
        except httpx.HTTPError as error:
            raise PresetQuestionAudioUnavailable() from error

        if response.status_code == 404:
            raise KeyError(audio_asset_id)
        if response.status_code != 200 or not response.content:
            raise PresetQuestionAudioUnavailable()
        return response.content


class PresetQuestionAudioService:
    def __init__(self, selector: TtsAssetSelector, repository: SupabasePresetQuestionAudioRepository) -> None:
        self.selector = selector
        self.repository = repository

    def read_wav(self, question_id: str) -> bytes:
        selected = self.selector.select_preset_question(question_id)
        if selected is None:
            raise KeyError(question_id)
        return self.repository.read_wav(str(selected["audioAssetId"]))
