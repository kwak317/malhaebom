from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.core.supabase_settings import SupabaseSettings

if TYPE_CHECKING:
    from app.core.auth import AuthenticatedUser


QUESTION_TTS_BUCKET_ID = "question-tts-audio"


class QuestionTtsPersistenceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class QuestionTtsRecord:
    audio_id: str
    user_id: str
    audio_path: str
    duration_ms: int
    expires_at: datetime


class SupabaseQuestionTtsRepository:
    """User-scoped adapter for temporary question TTS audio."""

    def __init__(self, settings: SupabaseSettings, http_client: httpx.Client | Any | None = None) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def create(self, user: AuthenticatedUser, audio: Any) -> QuestionTtsRecord:
        audio_id = str(uuid4())
        audio_path = f"{user.user_id}/{audio_id}/question.wav"
        self._upload(user, audio_path, audio.wav_bytes)
        values = {
            "id": audio_id,
            "user_id": user.user_id,
            "audio_path": audio_path,
            "duration_ms": audio.duration_ms,
        }
        try:
            return _record_from_row(self._insert_row(user, values))
        except QuestionTtsPersistenceError:
            try:
                self._remove_object(user, audio_path, allow_missing=True)
            except QuestionTtsPersistenceError:
                pass
            raise

    def read_wav(self, user: AuthenticatedUser, audio_id: str, now: datetime) -> bytes:
        response = self._request(
            "GET",
            f"/rest/v1/question_tts_audio?id=eq.{quote(audio_id, safe='-')}&select=*",
            user=user,
            expected=(200,),
        )
        rows = _json_list(response)
        if not rows:
            raise KeyError(audio_id)
        record = _record_from_row(rows[0])
        if record.user_id != user.user_id or record.expires_at <= _as_utc(now):
            raise KeyError(audio_id)
        response = self._request(
            "GET",
            f"/storage/v1/object/{QUESTION_TTS_BUCKET_ID}/{record.audio_path}",
            user=user,
            expected=(200,),
        )
        content = getattr(response, "content", None)
        if not isinstance(content, bytes) or not content:
            raise QuestionTtsPersistenceError("PERSISTENCE_FAILED", "질문 음성을 읽지 못했습니다.")
        return content

    def _upload(self, user: AuthenticatedUser, path: str, content: bytes) -> None:
        self._request(
            "POST",
            f"/storage/v1/object/{QUESTION_TTS_BUCKET_ID}/{path}",
            user=user,
            headers={"Content-Type": "audio/wav", "x-upsert": "false"},
            content=content,
            expected=(200, 201),
        )

    def _insert_row(self, user: AuthenticatedUser, values: dict[str, object]) -> dict[str, object]:
        response = self._request(
            "POST",
            "/rest/v1/question_tts_audio",
            user=user,
            headers={"Prefer": "return=representation"},
            json=values,
            expected=(201,),
        )
        rows = _json_list(response)
        if not rows:
            raise QuestionTtsPersistenceError("PERSISTENCE_FAILED", "질문 음성을 저장하지 못했습니다.")
        return rows[0]

    def _remove_object(self, user: AuthenticatedUser, path: str, allow_missing: bool) -> None:
        try:
            self._request(
                "DELETE",
                f"/storage/v1/object/{QUESTION_TTS_BUCKET_ID}",
                user=user,
                json={"prefixes": [path]},
            )
        except QuestionTtsPersistenceError as error:
            if allow_missing and error.code == "NOT_FOUND":
                return
            raise

    def _request(
        self,
        method: str,
        path: str,
        *,
        user: AuthenticatedUser,
        headers: dict[str, str] | None = None,
        expected: tuple[int, ...] = (200, 201, 204),
        **kwargs: Any,
    ) -> Any:
        request_headers = {
            "apikey": self.settings.publishable_key,
            "Authorization": f"Bearer {user.access_token}",
        }
        if headers:
            request_headers.update(headers)
        try:
            response = self.http.request(method, f"{self.settings.url}{path}", headers=request_headers, **kwargs)
        except httpx.HTTPError as error:
            raise QuestionTtsPersistenceError("PERSISTENCE_UNAVAILABLE", "저장소에 연결하지 못했습니다.") from error
        if response.status_code not in expected:
            code = "NOT_FOUND" if response.status_code == 404 else "PERSISTENCE_FAILED"
            raise QuestionTtsPersistenceError(code, "질문 음성 저장소 요청에 실패했습니다.")
        return response


class SupabaseExpiredQuestionTtsRepository:
    """Server-only adapter. Service role keys never cross the request boundary."""

    def __init__(self, settings: SupabaseSettings, http_client: httpx.Client | Any | None = None) -> None:
        if not settings.service_role_key:
            raise QuestionTtsPersistenceError("CONFIGURATION_ERROR", "만료 정리 설정이 없습니다.")
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def list_expired(self, now: datetime | None = None) -> list[dict[str, object]]:
        active_now = _as_utc(now or datetime.now(UTC)).isoformat().replace("+00:00", "Z")
        response = self._request(
            "GET",
            f"/rest/v1/question_tts_audio?expires_at=lte.{quote(active_now, safe=':-TZ')}&select=id,user_id,audio_path,duration_ms,expires_at",
        )
        return _json_list(response)

    def delete_expired(self, row: dict[str, object]) -> None:
        audio_id, audio_path = row.get("id"), row.get("audio_path")
        if not isinstance(audio_id, str) or not isinstance(audio_path, str):
            raise QuestionTtsPersistenceError("INVALID_RECORD", "만료 질문 음성 형식이 올바르지 않습니다.")
        self._remove_object(audio_path)
        self._request("DELETE", f"/rest/v1/question_tts_audio?id=eq.{quote(audio_id, safe='-')}")

    def mark_cleanup_failed(self, audio_id: str, code: str) -> None:
        self._request(
            "PATCH",
            f"/rest/v1/question_tts_audio?id=eq.{quote(audio_id, safe='-')}",
            json={
                "cleanup_attempted_at": datetime.now(UTC).isoformat(),
                "cleanup_error_code": code,
            },
        )

    def _remove_object(self, audio_path: str) -> None:
        try:
            self._request(
                "DELETE",
                f"/storage/v1/object/{QUESTION_TTS_BUCKET_ID}",
                json={"prefixes": [audio_path]},
            )
        except QuestionTtsPersistenceError as error:
            if error.code != "NOT_FOUND":
                raise QuestionTtsPersistenceError("STORAGE_DELETE_FAILED", "만료 질문 음성을 삭제하지 못했습니다.") from error

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {"apikey": self.settings.service_role_key or ""}
        try:
            response = self.http.request(method, f"{self.settings.url}{path}", headers=headers, **kwargs)
        except httpx.HTTPError as error:
            raise QuestionTtsPersistenceError("PERSISTENCE_UNAVAILABLE", "저장소에 연결하지 못했습니다.") from error
        if response.status_code not in (200, 201, 204):
            code = "NOT_FOUND" if response.status_code == 404 else "PERSISTENCE_FAILED"
            raise QuestionTtsPersistenceError(code, "만료 질문 음성 정리에 실패했습니다.")
        return response


def _json_list(response: Any) -> list[dict[str, object]]:
    try:
        value = response.json()
    except ValueError as error:
        raise QuestionTtsPersistenceError("PERSISTENCE_FAILED", "저장소 응답을 처리하지 못했습니다.") from error
    return value if isinstance(value, list) and all(isinstance(row, dict) for row in value) else []


def _record_from_row(row: dict[str, object]) -> QuestionTtsRecord:
    audio_id = row.get("id")
    user_id = row.get("user_id")
    audio_path = row.get("audio_path")
    duration_ms = row.get("duration_ms")
    expires_at = row.get("expires_at")
    if not isinstance(audio_id, str) or not isinstance(user_id, str) or not isinstance(audio_path, str) or not isinstance(duration_ms, int) or duration_ms <= 0 or not isinstance(expires_at, str):
        raise QuestionTtsPersistenceError("PERSISTENCE_FAILED", "저장된 질문 음성 형식이 올바르지 않습니다.")
    try:
        parsed_expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise QuestionTtsPersistenceError("PERSISTENCE_FAILED", "저장된 질문 음성 만료 시각이 올바르지 않습니다.") from error
    return QuestionTtsRecord(audio_id, user_id, audio_path, duration_ms, _as_utc(parsed_expires_at))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise QuestionTtsPersistenceError("PERSISTENCE_FAILED", "시간대 정보가 없습니다.")
    return value.astimezone(UTC)
