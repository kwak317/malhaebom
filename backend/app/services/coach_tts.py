from __future__ import annotations

import os
from collections.abc import Iterator

import httpx


class CoachTtsUnavailableError(RuntimeError):
    pass


class TtsWorkerClient:
    def __init__(self, base_url: str | None = None, http_client: httpx.Client | None = None) -> None:
        self.base_url = (base_url or os.getenv("TTS_WORKER_URL", "http://127.0.0.1:8100")).strip().rstrip("/")
        self.http = http_client or httpx.Client(timeout=120.0)

    def synthesize(self, text: str) -> bytes:
        normalized = text.strip()
        if not normalized or len(normalized) > 300:
            raise CoachTtsUnavailableError()
        try:
            response = self.http.post(f"{self.base_url}/internal/tts", json={"question": normalized})
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise CoachTtsUnavailableError() from error
        if not response.content or not response.headers.get("content-type", "").startswith("audio/wav"):
            raise CoachTtsUnavailableError()
        return response.content

    def synthesize_stream(self, text: str) -> Iterator[bytes]:
        normalized = text.strip()
        if not normalized or len(normalized) > 300:
            raise CoachTtsUnavailableError()
        try:
            with self.http.stream(
                "POST",
                f"{self.base_url}/internal/tts/stream",
                json={"question": normalized},
            ) as response:
                response.raise_for_status()
                if not response.headers.get("content-type", "").startswith("application/x-ndjson"):
                    raise CoachTtsUnavailableError()
                yield from response.iter_bytes()
        except httpx.HTTPError as error:
            raise CoachTtsUnavailableError() from error

    def synthesize_pcm_stream(self, text: str) -> Iterator[bytes]:
        normalized = text.strip()
        if not normalized or len(normalized) > 300:
            raise CoachTtsUnavailableError()
        try:
            with self.http.stream(
                "POST",
                f"{self.base_url}/internal/tts/pcm-stream",
                json={"question": normalized},
            ) as response:
                response.raise_for_status()
                if not response.headers.get("content-type", "").startswith("application/x-ndjson"):
                    raise CoachTtsUnavailableError()
                yield from response.iter_bytes()
        except httpx.HTTPError as error:
            raise CoachTtsUnavailableError() from error

    def is_ready(self) -> bool:
        try:
            response = self.http.get(f"{self.base_url}/health", timeout=2.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False
