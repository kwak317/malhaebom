from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import unquote

import httpx
from app.core.supabase_settings import SupabaseSettings

from app.schemas.ncs_competency import (
    NcsBackendCompetenciesResponse,
    NcsCompetencyOption,
)


logger = logging.getLogger(__name__)

NCS_API_URL = "https://apis.data.go.kr/B490007/hrdkapi/NCS005"
NCS_SOURCE_URL = "https://www.data.go.kr/data/15128213/openapi.do"
_JOB_CODES = ("20", "01", "02", "02")

# NCS005에는 KSA 구분이 없다. 아래 자기점검 문장은 능력단위 정의를 바탕으로 검토해 작성했다.
_REVIEWED_OPTIONS = (
    ("knowledge-foundations", "knowledge", "네트워크·미들웨어·데이터베이스 기초를 이해해요", "2001020232"),
    ("knowledge-data", "knowledge", "데이터 관계와 제약조건을 이해해요", "2001020205"),
    ("knowledge-interface", "knowledge", "인터페이스 요구사항과 설계를 이해해요", "2001020218"),
    ("skill-server", "skill", "서버 프로그램을 구현할 수 있어요", "2001020211"),
    ("skill-data", "skill", "데이터 입출력 기능을 구현할 수 있어요", "2001020205"),
    ("skill-testing", "skill", "테스트를 수행하고 결함을 고칠 수 있어요", "2001020227"),
    ("attitude-requirements", "attitude", "요구사항을 확인하고 검증하려고 해요", "2001020219"),
    ("attitude-improvement", "attitude", "문제가 있으면 코드를 개선하려고 해요", "2001020217"),
    ("attitude-deployment", "attitude", "배포 전 결과물을 검증하려고 해요", "2001020214"),
)


class NcsCompetencyUnavailable(RuntimeError):
    """NCS 조회 결과를 안전하게 자기점검 항목으로 제공할 수 없다."""


class NcsHttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


class NcsCompetencySettings:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @classmethod
    def from_env(cls) -> NcsCompetencySettings:
        api_key = os.getenv("NCS_API_KEY", "").strip()
        if not api_key:
            raise NcsCompetencyUnavailable("NCS 인증키가 설정되지 않았습니다.")
        return cls(api_key)


class NcsCompetencyService:
    def __init__(
        self,
        settings: NcsCompetencySettings,
        http_client: NcsHttpClient | None = None,
        snapshot_store: Any | None = None,
    ) -> None:
        self.snapshot_store = snapshot_store
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=10.0, follow_redirects=False)

    def backend_competencies(self) -> NcsBackendCompetenciesResponse:
        # First attempt always uses the official API; DB is only used on explicit retry.
        try:
            result = self._fetch_backend_competencies()
        except NcsCompetencyUnavailable as error:
            logger.warning("ncs_lookup_failed error_type=%s source=api",
                           type(error.__cause__ or error).__name__)
            raise
        result.fetched_at = datetime.now(UTC)
        if self.snapshot_store is not None:
            try:
                self.snapshot_store.save(result)
            except NcsCompetencyUnavailable:
                logger.warning("ncs_snapshot_save_failed")
        return result

    def stored_backend_competencies(self) -> NcsBackendCompetenciesResponse:
        if self.snapshot_store is None:
            raise NcsCompetencyUnavailable("저장된 NCS 목록을 불러올 수 없습니다.")
        result = self.snapshot_store.load()
        result.data_source = "cached"
        return result

    def _fetch_backend_competencies(self) -> NcsBackendCompetenciesResponse:
        try:
            response = self.http.get(
                NCS_API_URL,
                params={
                    "serviceKey": unquote(self.settings.api_key),
                    "pageNo": "1",
                    "numOfRows": "100",
                    "USG_YN": "Y",
                    "NCS_LCLAS_CD": _JOB_CODES[0],
                    "NCS_MCLAS_CD": _JOB_CODES[1],
                    "NCS_SCLAS_CD": _JOB_CODES[2],
                    "NCS_SUBD_CD": _JOB_CODES[3],
                },
            )
            if response.status_code != 200:
                raise NcsCompetencyUnavailable("NCS 정보를 불러오지 못했습니다.")
            payload = response.json()["response"]
            if str(payload["header"]["resultCode"]) != "00":
                raise NcsCompetencyUnavailable("NCS 정보를 불러오지 못했습니다.")
            items = payload["body"]["items"]["item"]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise NcsCompetencyUnavailable("NCS 정보를 불러오지 못했습니다.") from error

        rows = items if isinstance(items, list) else [items]
        units: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            if tuple(row.get(code) for code in (
                "NCS_LCLAS_CD", "NCS_MCLAS_CD", "NCS_SCLAS_CD", "NCS_SUBD_CD"
            )) != _JOB_CODES or row.get("USG_YN") != "Y":
                continue
            unit_code = row.get("NCS_CL_CD")
            unit_name = row.get("COMPE_UNIT_NAME")
            unit_definition = row.get("COMPE_UNIT_DEF")
            if not all(isinstance(value, str) and value.strip() for value in (
                unit_code, unit_name, unit_definition
            )):
                continue
            units[unit_code.split("_")[0]] = row

        if not all(unit_code in units for _, _, _, unit_code in _REVIEWED_OPTIONS):
            raise NcsCompetencyUnavailable("검토한 백엔드 개발 NCS 능력단위를 확인하지 못했습니다.")

        options = [
            NcsCompetencyOption(
                id=option_id,
                category=category,
                label=label,
                ncs_unit_code=units[unit_code]["NCS_CL_CD"],
                ncs_unit_name=units[unit_code]["COMPE_UNIT_NAME"],
            )
            for option_id, category, label, unit_code in _REVIEWED_OPTIONS
        ]
        return NcsBackendCompetenciesResponse(
            job_name="응용SW엔지니어링",
            source_url=NCS_SOURCE_URL,
            options=options,
        )


class UnavailableNcsCompetencyService:
    def __init__(self, message: str) -> None:
        self.message = message

    def backend_competencies(self) -> NcsBackendCompetenciesResponse:
        raise NcsCompetencyUnavailable(self.message)

    def stored_backend_competencies(self) -> NcsBackendCompetenciesResponse:
        raise NcsCompetencyUnavailable(self.message)


class SupabaseNcsSnapshotStore:
    """Server-only shared reference snapshot; no account data or client-supplied rows."""

    def __init__(self, settings: SupabaseSettings, http_client: Any | None = None) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=5.0)

    def _request(self, method: str, **kwargs: Any) -> Any:
        key = self.settings.service_role_key
        if not key:
            raise NcsCompetencyUnavailable("저장된 NCS 목록을 불러올 수 없습니다.")
        try:
            response = self.http.request(
                method, self.settings.url + "/rest/v1/ncs_backend_snapshots",
                headers={"apikey": key, "Authorization": "Bearer " + key,
                         "Prefer": "resolution=merge-duplicates,return=minimal"},
                **kwargs,
            )
            if response.status_code >= 300:
                raise NcsCompetencyUnavailable("저장된 NCS 목록을 불러올 수 없습니다.")
            return response
        except httpx.HTTPError as error:
            raise NcsCompetencyUnavailable("저장된 NCS 목록을 불러올 수 없습니다.") from error

    def save(self, result: NcsBackendCompetenciesResponse) -> None:
        validate_snapshot(result)
        self._request("POST", params={"on_conflict": "id"},
                      json={"id": "backend", "payload": result.model_dump(mode="json")})

    def load(self) -> NcsBackendCompetenciesResponse:
        try:
            rows = self._request("GET", params={"id": "eq.backend", "select": "payload", "limit": "1"}).json()
            if not isinstance(rows, list) or len(rows) != 1:
                raise ValueError("Missing snapshot")
            result = NcsBackendCompetenciesResponse.model_validate(rows[0]["payload"])
            validate_snapshot(result)
            return result
        except (ValueError, KeyError, TypeError) as error:
            raise NcsCompetencyUnavailable("저장된 NCS 목록을 확인하지 못했습니다.") from error


def validate_snapshot(result: NcsBackendCompetenciesResponse) -> None:
    if (result.job_name != "응용SW엔지니어링" or result.source_url != NCS_SOURCE_URL
            or result.fetched_at is None or len(result.options) != len(_REVIEWED_OPTIONS)):
        raise NcsCompetencyUnavailable("저장된 NCS 목록을 확인하지 못했습니다.")
    options = {option.id: option for option in result.options}
    for option_id, category, label, unit_code in _REVIEWED_OPTIONS:
        option = options.get(option_id)
        if (option is None or option.category != category or option.label != label
                or option.ncs_unit_code.split("_")[0] != unit_code or not option.ncs_unit_name.strip()):
            raise NcsCompetencyUnavailable("저장된 NCS 목록을 확인하지 못했습니다.")
