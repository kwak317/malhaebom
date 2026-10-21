"""Cloud Run shared PlayMCP credentials; generation CAS serializes token rotation."""
from __future__ import annotations

import logging
import math
import threading
import time
from urllib.parse import quote

import httpx

from app.services.saramin_recommendation import SaraminRecommendationUnavailable

_LOGGER = logging.getLogger(__name__)
_AUTH_ERROR = "공고 검색 인증을 확인하지 못했습니다. PlayMCP 연결을 다시 확인해 주세요."
_TOKEN_ENDPOINT = "https://playauth.kakao.com/playmcp/oauth2/token"


class GcsAuthObject:
    def __init__(self, bucket: str, *, http_client=None):
        self.bucket = bucket
        self.http = http_client or httpx.Client(timeout=15, trust_env=False)

    def _headers(self):
        response = self.http.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        response.raise_for_status()
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def read(self):
        url = f"https://storage.googleapis.com/storage/v1/b/{quote(self.bucket, safe='')}/o/auth.json"
        headers = self._headers()
        metadata = self.http.get(url, headers=headers)
        metadata.raise_for_status()
        generation = metadata.json()["generation"]
        response = self.http.get(url, headers=headers, params={"alt": "media", "generation": generation})
        response.raise_for_status()
        return response.json(), generation

    def write(self, data, generation):
        response = self.http.post(
            f"https://storage.googleapis.com/upload/storage/v1/b/{quote(self.bucket, safe='')}/o",
            headers={**self._headers(), "Content-Type": "application/json"},
            params={"uploadType": "media", "name": "auth.json", "ifGenerationMatch": generation},
            json=data,
        )
        if response.status_code == 412:
            return None
        response.raise_for_status()
        return response.json()["generation"]


class CloudPlayMcpTokenStore:
    def __init__(self, storage, *, http_client=None):
        self.storage = storage
        self.http = http_client or httpx.Client(timeout=15, trust_env=False)
        self.lock = threading.Lock()
        self.last_issued = None

    def refresh_after_rejection(self, rejected_token):
        return self.access_token(refresh=True, rejected_token=rejected_token)

    def access_token(self, *, refresh=False, rejected_token=None):
        with self.lock:
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    data, generation = self.storage.read()
                    token = data["access_token"]
                    expires_at = float(data["expires_at"])
                    if not isinstance(token, str) or not token.strip() or not math.isfinite(expires_at):
                        raise ValueError("invalid credentials")
                    if data.get("refresh_in_progress"):
                        time.sleep(0.2)
                        continue
                    if expires_at > time.time() + 60 and (not refresh or token != (rejected_token if rejected_token is not None else self.last_issued)):
                        self.last_issued = token
                        return token
                    if not data.get("refresh_token") or not data.get("client_id"):
                        raise ValueError("missing refresh credentials")
                    locked_generation = self.storage.write({**data, "refresh_in_progress": True}, generation)
                    if locked_generation is None:
                        continue
                    # Never automatically steal an interrupted refresh: the provider may have
                    # rotated the token already. Reauthentication is required in that case.
                    response = self.http.post(_TOKEN_ENDPOINT, data={
                        "grant_type": "refresh_token", "refresh_token": data["refresh_token"],
                        "client_id": data["client_id"],
                    })
                    response.raise_for_status()
                    payload = response.json()
                    token = payload["access_token"]
                    lifetime = float(payload["expires_in"])
                    if not isinstance(token, str) or not token.strip() or not math.isfinite(lifetime) or lifetime <= 60:
                        raise ValueError("invalid refreshed credentials")
                    updated = {**data, "access_token": token,
                               "refresh_token": payload.get("refresh_token") or data["refresh_token"],
                               "expires_at": time.time() + lifetime, "refresh_in_progress": False}
                    if self.storage.write(updated, locked_generation) is None:
                        raise ValueError("credential persistence conflict")
                    self.last_issued = token
                    return token
                raise TimeoutError("refresh wait timeout")
            except Exception as error:
                _LOGGER.warning("PlayMCP shared authentication failure: %s", type(error).__name__)
                raise SaraminRecommendationUnavailable(_AUTH_ERROR) from None
