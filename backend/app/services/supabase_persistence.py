from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from app.core.auth import AuthenticatedUser
from app.core.supabase_settings import SupabaseSettings


BUCKET_ID = "analysis-audio"
HISTORY_SELECT = (
    "*,answer_revisions(id,confirmed_text,answer_segments,confirmed_at,delivery_metrics,"
    "coaching_runs(response,created_at,model_name,prompt_version,skill_version,criteria_version))"
)


class SupabasePersistenceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SupabaseAnalysisRepository:
    """Supabase REST/Storage adapter. Normal calls always retain the user's RLS scope."""

    def __init__(self, settings: SupabaseSettings, http_client: httpx.Client | Any | None = None) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def create_job(
        self,
        user: AuthenticatedUser,
        job_id: str,
        metadata: dict[str, object],
        content: bytes,
        filename: str,
        content_type: str | None,
    ) -> dict[str, object]:
        suffix = _safe_suffix(filename)
        audio_path = f"{user.user_id}/{job_id}/original{suffix}"
        self._upload(user, audio_path, content, content_type)
        record = {**metadata, "id": job_id, "user_id": user.user_id, "audio_path": audio_path, "audio_content_type": content_type}
        try:
            return self._insert_row(user, record)
        except SupabasePersistenceError:
            try:
                self._remove_object(user, audio_path, allow_missing=True)
            except SupabasePersistenceError:
                pass
            raise

    def get_job(self, user: AuthenticatedUser, job_id: str) -> dict[str, object]:
        response = self._request(
            "GET", f"/rest/v1/analysis_jobs?id=eq.{job_id}&expires_at=gt.{quote(datetime.now(timezone.utc).isoformat(), safe='')}&select=*", user=user
        )
        rows = _json_list(response)
        if not rows:
            raise KeyError(job_id)
        return rows[0]

    def get_attempt_one(self, user: AuthenticatedUser, practice_session_id: str) -> dict[str, object]:
        session_id = quote(practice_session_id, safe="")
        now = quote(datetime.now(timezone.utc).isoformat(), safe="")
        response = self._request(
            "GET",
            f"/rest/v1/analysis_jobs?practice_session_id=eq.{session_id}&attempt_no=eq.1&status=eq.completed&expires_at=gt.{now}&select=*",
            user=user,
        )
        rows = _json_list(response)
        if not rows:
            raise KeyError(practice_session_id)
        return rows[0]

    def get_practice_session(
        self, user: AuthenticatedUser, practice_session_id: str
    ) -> dict[str, object]:
        session_id = quote(practice_session_id, safe="")
        response = self._request(
            "GET",
            "/rest/v1/practice_sessions"
            f"?id=eq.{session_id}&select=id,job_posting_id,question_type,question_id,"
            "custom_question_text,expires_at,applicant_context",
            user=user,
        )
        rows = _json_list(response)
        if not rows:
            raise KeyError(practice_session_id)
        return rows[0]

    def get_stt_hint_context(
        self, user: AuthenticatedUser, practice_session_id: str
    ) -> list[str]:
        session = self.get_practice_session(user, practice_session_id)
        context: list[str] = []

        custom_question = session.get("custom_question_text")
        if isinstance(custom_question, str) and custom_question.strip():
            context.append(custom_question.strip())

        job_posting_id = session.get("job_posting_id")
        if not isinstance(job_posting_id, str) or not job_posting_id:
            return context

        posting_id = quote(job_posting_id, safe="")
        posting_response = self._request(
            "GET",
            f"/rest/v1/job_postings?id=eq.{posting_id}&select=title",
            user=user,
        )
        posting_rows = _json_list(posting_response)
        if posting_rows:
            title = posting_rows[0].get("title")
            if isinstance(title, str) and title.strip():
                context.append(title.strip())

        session_id = quote(practice_session_id, safe="")
        requirement_response = self._request(
            "GET",
            "/rest/v1/practice_session_requirements"
            f"?practice_session_id=eq.{session_id}"
            "&select=job_requirements(requirement_text)",
            user=user,
        )
        for row in _json_list(requirement_response):
            requirement = row.get("job_requirements")
            if not isinstance(requirement, dict):
                continue
            text = requirement.get("requirement_text")
            if isinstance(text, str) and text.strip():
                context.append(text.strip())
        return context

    def list_completed_jobs(self, user: AuthenticatedUser, limit: int = 100) -> list[dict[str, object]]:
        now = quote(datetime.now(timezone.utc).isoformat(), safe="")
        response = self._request(
            "GET",
            f"/rest/v1/analysis_jobs?status=eq.completed&expires_at=gt.{now}"
            f"&select={HISTORY_SELECT}&order=completed_at.desc&limit={limit}",
            user=user,
        )
        return _json_list(response)

    def get_completed_session_jobs(self, user: AuthenticatedUser, practice_session_id: str) -> list[dict[str, object]]:
        session_id = quote(practice_session_id, safe="")
        now = quote(datetime.now(timezone.utc).isoformat(), safe="")
        response = self._request(
            "GET",
            f"/rest/v1/analysis_jobs?practice_session_id=eq.{session_id}"
            f"&status=eq.completed&expires_at=gt.{now}&select={HISTORY_SELECT}"
            "&order=attempt_no.asc",
            user=user,
        )
        rows = _json_list(response)
        if not rows:
            raise KeyError(practice_session_id)
        return rows

    def get_session_jobs(self, user: AuthenticatedUser, practice_session_id: str) -> list[dict[str, object]]:
        session_id = quote(practice_session_id, safe="")
        response = self._request(
            "GET",
            f"/rest/v1/analysis_jobs?practice_session_id=eq.{session_id}&select=*&order=attempt_no.asc",
            user=user,
        )
        rows = _json_list(response)
        if not rows:
            raise KeyError(practice_session_id)
        return rows

    def delete_session_jobs(self, user: AuthenticatedUser, practice_session_id: str, rows: list[dict[str, object]]) -> None:
        for row in rows:
            audio_path = row.get("audio_path")
            if not isinstance(audio_path, str):
                raise SupabasePersistenceError("INVALID_JOB", "저장된 음성 경로가 올바르지 않습니다.")
            self._remove_object(user, audio_path, allow_missing=True)
        session_id = quote(practice_session_id, safe="")
        self._request("DELETE", f"/rest/v1/analysis_jobs?practice_session_id=eq.{session_id}", user=user)

    def mark_processing(self, user: AuthenticatedUser, job_id: str) -> None:
        self._update_row(user, job_id, {"status": "processing"})

    def mark_completed(self, user: AuthenticatedUser, job_id: str, result: dict[str, object], delivery: dict[str, object]) -> None:
        self._update_row(user, job_id, {"status": "completed", "result": result, "delivery": delivery, "completed_at": datetime.now(timezone.utc).isoformat()})

    def mark_failed(self, user: AuthenticatedUser, job_id: str, code: str, message: str) -> None:
        self._update_row(user, job_id, {"status": "failed", "error": {"code": code, "message": message}})

    def delete_job(self, user: AuthenticatedUser, job_id: str) -> None:
        row = self.get_job(user, job_id)
        audio_path = row.get("audio_path")
        if not isinstance(audio_path, str):
            raise SupabasePersistenceError("INVALID_JOB", "저장된 음성 경로가 올바르지 않습니다.")
        self._remove_object(user, audio_path, allow_missing=True)
        self._request("DELETE", f"/rest/v1/analysis_jobs?id=eq.{job_id}", user=user)

    def _upload(self, user: AuthenticatedUser, path: str, content: bytes, content_type: str | None) -> None:
        headers = {"Content-Type": content_type or "application/octet-stream", "x-upsert": "false"}
        self._request("POST", f"/storage/v1/object/{BUCKET_ID}/{path}", user=user, headers=headers, content=content, expected=(200, 201))

    def _insert_row(self, user: AuthenticatedUser, record: dict[str, object]) -> dict[str, object]:
        response = self._request(
            "POST", "/rest/v1/analysis_jobs", user=user,
            headers={"Prefer": "return=representation"}, json=record, expected=(201,),
        )
        rows = _json_list(response)
        if not rows:
            raise SupabasePersistenceError("PERSISTENCE_FAILED", "분석 작업을 저장하지 못했습니다.")
        return rows[0]

    def _update_row(self, user: AuthenticatedUser, job_id: str, values: dict[str, object]) -> None:
        response = self._request(
            "PATCH", f"/rest/v1/analysis_jobs?id=eq.{job_id}&expires_at=gt.{quote(datetime.now(timezone.utc).isoformat(), safe='')}", user=user,
            headers={"Prefer": "return=representation"}, json=values,
        )
        if not _json_list(response):
            raise KeyError(job_id)

    def _remove_object(self, user: AuthenticatedUser, path: str, allow_missing: bool) -> None:
        try:
            self._request("DELETE", f"/storage/v1/object/{BUCKET_ID}", user=user, json={"prefixes": [path]})
        except SupabasePersistenceError as error:
            if allow_missing and error.code == "NOT_FOUND":
                return
            raise

    def _request(self, method: str, path: str, *, user: AuthenticatedUser, headers: dict[str, str] | None = None, expected: tuple[int, ...] = (200, 201, 204), **kwargs: Any) -> Any:
        request_headers = {"apikey": self.settings.publishable_key, "Authorization": f"Bearer {user.access_token}"}
        if headers:
            request_headers.update(headers)
        try:
            response = self.http.request(method, f"{self.settings.url}{path}", headers=request_headers, **kwargs)
        except httpx.HTTPError as error:
            raise SupabasePersistenceError("PERSISTENCE_UNAVAILABLE", "저장소에 연결하지 못했습니다.") from error
        if response.status_code not in expected:
            code = "NOT_FOUND" if response.status_code == 404 else "PERSISTENCE_FAILED"
            raise SupabasePersistenceError(code, _persistence_failure_message(response.status_code))
        return response


def _safe_suffix(filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return f".{suffix}" if suffix in {"wav", "webm", "mp3"} else ".bin"


def _persistence_failure_message(status_code: int) -> str:
    if status_code == 401:
        return "분석 작업 저장소 인증에 실패했습니다. Supabase 키 설정을 확인해 주세요. (HTTP 401)"
    if status_code == 403:
        return "분석 작업 저장소 접근이 거부되었습니다. Storage RLS 정책을 확인해 주세요. (HTTP 403)"
    if status_code == 404:
        return "분석 작업 저장소를 찾을 수 없습니다. 버킷 또는 테이블 설정을 확인해 주세요. (HTTP 404)"
    return f"분석 작업 저장소 요청에 실패했습니다. (HTTP {status_code})"


def _json_list(response: Any) -> list[dict[str, object]]:
    try:
        value = response.json()
    except ValueError as error:
        raise SupabasePersistenceError("PERSISTENCE_FAILED", "저장소 응답을 처리하지 못했습니다.") from error
    return value if isinstance(value, list) else []


class SupabaseExpiredJobCleanupRepository:
    """Server-only cleanup adapter. It never exposes the service-role key to requests."""

    def __init__(self, settings: SupabaseSettings, http_client: httpx.Client | Any | None = None) -> None:
        if not settings.service_role_key:
            raise SupabasePersistenceError("CONFIGURATION_ERROR", "만료 정리 설정이 없습니다.")
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=20.0)

    def list_expired_jobs(self) -> list[dict[str, object]]:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        response = self._request("GET", f"/rest/v1/analysis_jobs?expires_at=lte.{now}&select=id,audio_path")
        return _json_list(response)

    def delete_expired_job(self, job: dict[str, object]) -> None:
        job_id, path = job.get("id"), job.get("audio_path")
        if not isinstance(job_id, str) or not isinstance(path, str):
            raise SupabasePersistenceError("INVALID_JOB", "만료 Job 형식이 올바르지 않습니다.")
        self._remove_object(path)
        self._request("DELETE", f"/rest/v1/analysis_jobs?id=eq.{job_id}")

    def mark_cleanup_failed(self, job_id: str, code: str) -> None:
        self._request("PATCH", f"/rest/v1/analysis_jobs?id=eq.{job_id}", json={"cleanup_attempted_at": datetime.now(timezone.utc).isoformat(), "cleanup_error_code": code})

    def _remove_object(self, path: str) -> None:
        try:
            self._request("DELETE", f"/storage/v1/object/{BUCKET_ID}", json={"prefixes": [path]})
        except SupabasePersistenceError as error:
            if error.code != "NOT_FOUND":
                raise

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {"apikey": self.settings.service_role_key or ""}
        try:
            response = self.http.request(method, f"{self.settings.url}{path}", headers=headers, **kwargs)
        except httpx.HTTPError as error:
            raise SupabasePersistenceError("PERSISTENCE_UNAVAILABLE", "저장소에 연결하지 못했습니다.") from error
        if response.status_code not in (200, 201, 204):
            code = "NOT_FOUND" if response.status_code == 404 else "STORAGE_DELETE_FAILED" if "/storage/" in path else "PERSISTENCE_FAILED"
            raise SupabasePersistenceError(code, "만료 분석 작업 정리에 실패했습니다.")
        return response
