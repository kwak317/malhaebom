from __future__ import annotations

import html
import os
import re
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from app.schemas.alio_recruitment import (
    AlioRecruitmentSearchResponse,
    AlioRecruitmentSummary,
)


DEFAULT_ALIO_RECRUITMENT_API_URL = (
    "https://opendata.alio.go.kr/new/odaApiMng/recrutInquiryAjaxList.do"
)
_ALIO_HOST = "opendata.alio.go.kr"
_KEY_PARAMETER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_ANALYSIS_SOURCE_FIELDS = (
    ("aplyQlfcCn", "지원자격"),
    ("prefCn", "우대사항"),
    ("prefCondCn", "우대조건"),
    ("acbgCondNmLst", "학력요건"),
    ("ncsCdNmLst", "직무분류"),
    ("disqlfcRsn", "결격사유"),
)


class AlioRecruitmentUnavailable(RuntimeError):
    """Raised when ALIO recruitment search cannot be performed safely."""


class AlioHttpClient(Protocol):
    def post(self, url: str, **kwargs: Any) -> Any: ...


class AlioRecruitmentSettings:
    def __init__(self, api_key: str, api_url: str, api_key_param: str) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.api_key_param = api_key_param

    @classmethod
    def from_env(cls) -> "AlioRecruitmentSettings":
        api_key = os.getenv("ALIO_API_KEY", "").strip()
        if not api_key:
            raise AlioRecruitmentUnavailable("ALIO 인증키가 설정되지 않았습니다.")

        api_url = (
            os.getenv("ALIO_RECRUITMENT_API_URL", "").strip()
            or DEFAULT_ALIO_RECRUITMENT_API_URL
        )
        parsed_url = urlparse(api_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != _ALIO_HOST
            or parsed_url.username
            or parsed_url.password
        ):
            raise AlioRecruitmentUnavailable(
                "ALIO 채용 API URL 설정을 확인해 주세요."
            )

        api_key_param = os.getenv("ALIO_API_KEY_PARAM", "").strip() or "authKey"
        if not _KEY_PARAMETER_PATTERN.fullmatch(api_key_param):
            raise AlioRecruitmentUnavailable(
                "ALIO 인증키 파라미터 설정을 확인해 주세요."
            )
        return cls(api_key=api_key, api_url=api_url, api_key_param=api_key_param)


class AlioRecruitmentService:
    def __init__(
        self,
        settings: AlioRecruitmentSettings,
        http_client: AlioHttpClient | None = None,
    ) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=10.0)

    def search(
        self,
        *,
        query: str,
        page: int = 1,
        page_size: int = 10,
    ) -> AlioRecruitmentSearchResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("검색어를 입력해 주세요.")

        rows, total_count = self._search_rows(
            query=normalized_query, page=page, page_size=page_size
        )
        recruitments = [
            recruitment
            for row in rows
            if (recruitment := _to_summary(row)) is not None
        ]
        return AlioRecruitmentSearchResponse(
            query=normalized_query,
            page=page,
            page_size=page_size,
            total_count=total_count if total_count >= 0 else len(recruitments),
            recruitments=recruitments,
        )

    def get_analysis_source(
        self, *, announcement_id: int, title: str
    ) -> str | None:
        """ALIO가 제공한 지원자격·우대사항을 분석 근거로 다시 가져온다."""
        normalized_title = title.strip()
        if not normalized_title:
            return None
        rows, _ = self._search_rows(
            query=normalized_title, page=1, page_size=10
        )
        row = next(
            (
                candidate
                for candidate in rows
                if candidate.get("recrutPblntSn") == announcement_id
            ),
            None,
        )
        return _to_analysis_source(row) if row is not None else None

    def _search_rows(
        self, *, query: str, page: int, page_size: int
    ) -> tuple[list[dict[str, object]], int]:
        request_data = {
            "pageNo": str(page),
            "numOfRows": str(page_size),
            "recrutPbancTtl": query,
            "ongoingYn": "Y",
            self.settings.api_key_param: self.settings.api_key,
        }
        try:
            response = self.http.post(
                self.settings.api_url,
                data=request_data,
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as error:
            raise AlioRecruitmentUnavailable(
                "ALIO 공고 검색에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
            ) from error

        if getattr(response, "status_code", None) != 200:
            raise AlioRecruitmentUnavailable(
                "ALIO 공고 검색에 실패했습니다. 잠시 후 다시 시도해 주세요."
            )

        try:
            payload = response.json()
        except ValueError as error:
            raise AlioRecruitmentUnavailable(
                "ALIO 공고 검색 응답을 처리하지 못했습니다."
            ) from error

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict) or data.get("resultCode") != 200:
            raise AlioRecruitmentUnavailable(
                "ALIO 공고 검색 응답을 처리하지 못했습니다."
            )
        rows = data.get("result")
        if not isinstance(rows, list):
            raise AlioRecruitmentUnavailable(
                "ALIO 공고 검색 응답을 처리하지 못했습니다."
            )

        total_count = data.get("totalCount")
        normalized_rows = [row for row in rows if isinstance(row, dict)]
        return (
            normalized_rows,
            total_count if isinstance(total_count, int) and total_count >= 0 else -1,
        )


class UnavailableAlioRecruitmentService:
    def __init__(self, message: str) -> None:
        self.message = message

    def search(self, **_: Any) -> AlioRecruitmentSearchResponse:
        raise AlioRecruitmentUnavailable(self.message)

    def get_analysis_source(self, **_: Any) -> str | None:
        raise AlioRecruitmentUnavailable(self.message)


def _to_summary(row: dict[str, object]) -> AlioRecruitmentSummary | None:
    announcement_id = row.get("recrutPblntSn")
    company = _as_nonempty_string(row.get("instNm"))
    title = _as_nonempty_string(row.get("recrutPbancTtl"))
    if not isinstance(announcement_id, int) or not company or not title:
        return None
    return AlioRecruitmentSummary(
        announcement_id=announcement_id,
        company=company,
        title=title,
        source_url=_safe_source_url(row.get("srcUrl")),
        announced_at=_to_date(row.get("pbancBgngYmd")),
        deadline=_to_date(row.get("pbancEndYmd")),
        location=_as_nonempty_string(row.get("workRgnNmLst")),
        employment_type=_as_nonempty_string(row.get("hireTypeNmLst")),
        recruitment_type=_as_nonempty_string(row.get("recrutSeNm")),
    )


def _as_nonempty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _safe_source_url(value: object) -> str | None:
    url = _as_nonempty_string(value)
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url


def _to_analysis_source(row: dict[str, object]) -> str | None:
    parts = [
        f"{label}: {value}"
        for field, label in _ANALYSIS_SOURCE_FIELDS
        if (value := _analysis_source_text(row.get(field)))
    ]
    return "\n".join(parts) or None


def _analysis_source_text(value: object) -> str | None:
    if isinstance(value, list):
        text = " ".join(item for item in value if isinstance(item, str))
    elif isinstance(value, str):
        text = value
    else:
        return None
    normalized = re.sub(r"<[^>]+>", " ", html.unescape(text))
    normalized = " ".join(normalized.split())
    return normalized or None


def _to_date(value: object):
    if not isinstance(value, str) or not re.fullmatch(r"\d{8}", value):
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None
