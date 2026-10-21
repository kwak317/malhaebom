from __future__ import annotations

import html
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlencode, urlparse

import httpx

from app.schemas.public_employment_recruitment import (
    PublicEmploymentRecruitmentSearchResponse,
    PublicEmploymentRecruitmentSummary,
)


DEFAULT_PUBLIC_EMPLOYMENT_API_URL = "https://apis.data.go.kr/1760000/PblJobService"
_PUBLIC_EMPLOYMENT_HOST = "apis.data.go.kr"
_SEARCH_SAMPLE_SIZE = 100


class PublicEmploymentRecruitmentUnavailable(RuntimeError):
    """인사혁신처 공공취업정보를 안전하게 조회할 수 없을 때 발생한다."""


class PublicEmploymentHttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


class PublicEmploymentRecruitmentSettings:
    def __init__(self, api_key: str, api_url: str) -> None:
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")

    @classmethod
    def from_env(cls) -> "PublicEmploymentRecruitmentSettings":
        api_key = os.getenv("MPO_PUBLIC_JOB_API_KEY", "").strip()
        if not api_key:
            raise PublicEmploymentRecruitmentUnavailable(
                "인사혁신처 공공취업정보 인증키가 설정되지 않았습니다."
            )

        api_url = (
            os.getenv("MPO_PUBLIC_JOB_API_URL", "").strip()
            or DEFAULT_PUBLIC_EMPLOYMENT_API_URL
        ).rstrip("/")
        parsed_url = urlparse(api_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != _PUBLIC_EMPLOYMENT_HOST
            or parsed_url.username
            or parsed_url.password
            or parsed_url.path != "/1760000/PblJobService"
        ):
            raise PublicEmploymentRecruitmentUnavailable(
                "인사혁신처 공공취업정보 API URL 설정을 확인해 주세요."
            )
        return cls(api_key=api_key, api_url=api_url)


class PublicEmploymentRecruitmentService:
    def __init__(
        self,
        settings: PublicEmploymentRecruitmentSettings,
        http_client: PublicEmploymentHttpClient | None = None,
    ) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=10.0)

    def search(
        self,
        *,
        query: str,
        page: int = 1,
        page_size: int = 10,
    ) -> PublicEmploymentRecruitmentSearchResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("검색어를 입력해 주세요.")

        root = self._request_xml(
            "getList",
            {
                "pageNo": str(page),
                # 제공자의 Kwrd 필터는 현재 전체 공고를 반환한다. 최신 공고 100건을
                # 가져와 제목·기관·공고 분류에서 서버가 직접 동일 키워드를 찾는다.
                "numOfRows": str(max(page_size, _SEARCH_SAMPLE_SIZE)),
                # 공고 유형과 기관 구분을 비우면 제공자가 전체 공고 범위에서 검색한다.
                "Pblanc_ty": "",
                "Instt_se": "",
                "Sort_order": "2",
                "Kwrd": normalized_query,
            },
        )
        recruitments = [
            recruitment
            for item in _find_items(root)
            if (recruitment := _to_summary(item)) is not None
            and _matches_query(recruitment, normalized_query)
        ]
        return PublicEmploymentRecruitmentSearchResponse(
            query=normalized_query,
            page=page,
            page_size=page_size,
            total_count=len(recruitments),
            recruitments=recruitments[:page_size],
        )

    def get_analysis_source(self, *, announcement_id: int) -> tuple[str, str]:
        root = self._request_xml("getItem", {"idx": str(announcement_id)})
        item = next(iter(_find_items(root)), None)
        if item is None:
            raise PublicEmploymentRecruitmentUnavailable(
                "선택한 공공취업정보 공고 원문을 찾지 못했습니다."
            )
        source_text = _normalize_text(_item_text(item, "contents") or "")
        if len(source_text) < 20:
            raise PublicEmploymentRecruitmentUnavailable(
                "공공취업정보 공고 원문에서 분석할 텍스트를 찾지 못했습니다."
            )
        source_url = next(
            (
                url
                for field in ("link01", "link02", "link03")
                if (url := _safe_source_url(_item_text(item, field))) is not None
            ),
            None,
        )
        if source_url is None:
            raise PublicEmploymentRecruitmentUnavailable(
                "공고 원문 링크가 없어 요구사항 분석을 진행할 수 없습니다."
            )
        return source_text, source_url

    def _request_xml(self, operation: str, parameters: dict[str, str]) -> ET.Element:
        # 데이터포털이 발급한 serviceKey는 이미 URL 인코딩된 값이다. httpx params에
        # 넣으면 %가 다시 인코딩되어 403이 되므로, 키만 발급값 그대로 유지한다.
        query = urlencode(parameters)
        url = f"{self.settings.api_url}/{operation}?serviceKey={self.settings.api_key}&{query}"
        try:
            response = self.http.get(url, headers={"Accept": "application/xml"})
        except httpx.HTTPError as error:
            raise PublicEmploymentRecruitmentUnavailable(
                "인사혁신처 공공취업정보 공고 검색에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
            ) from error

        if getattr(response, "status_code", None) != 200:
            raise PublicEmploymentRecruitmentUnavailable(
                "인사혁신처 공공취업정보 공고 검색에 실패했습니다. 잠시 후 다시 시도해 주세요."
            )
        try:
            root = ET.fromstring(response.content)
        except (ET.ParseError, TypeError) as error:
            raise PublicEmploymentRecruitmentUnavailable(
                "인사혁신처 공공취업정보 응답을 처리하지 못했습니다."
            ) from error
        result_code = _find_text(root, "resultCode")
        if result_code and result_code != "00":
            raise PublicEmploymentRecruitmentUnavailable(
                "인사혁신처 공공취업정보 공고 검색에 실패했습니다. 잠시 후 다시 시도해 주세요."
            )
        return root


class UnavailablePublicEmploymentRecruitmentService:
    def __init__(self, message: str) -> None:
        self.message = message

    def search(self, **_: Any) -> PublicEmploymentRecruitmentSearchResponse:
        raise PublicEmploymentRecruitmentUnavailable(self.message)

    def get_analysis_source(self, **_: Any) -> tuple[str, str]:
        raise PublicEmploymentRecruitmentUnavailable(self.message)


def _find_items(root: ET.Element) -> list[ET.Element]:
    return list(root.findall(".//items/item")) or list(root.findall(".//item"))


def _find_text(root: ET.Element, field: str) -> str | None:
    element = root.find(f".//{field}")
    return _normalize_text(element.text) if element is not None and element.text else None


def _item_text(item: ET.Element, field: str) -> str | None:
    element = item.find(field)
    return _normalize_text(element.text) if element is not None and element.text else None


def _to_summary(item: ET.Element) -> PublicEmploymentRecruitmentSummary | None:
    announcement_id = _as_int(_item_text(item, "idx"))
    company = _item_text(item, "insttname")
    title = _item_text(item, "title")
    if announcement_id is None or not company or not title:
        return None
    return PublicEmploymentRecruitmentSummary(
        announcement_id=announcement_id,
        company=company,
        title=title,
        announced_at=_to_date(_item_text(item, "regdate")),
        deadline=_to_date(_item_text(item, "enddate")),
        location=_item_text(item, "areanm"),
        employment_type=_item_text(item, "type01"),
        recruitment_type=_item_text(item, "type02"),
    )


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _safe_source_url(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.startswith("www."):
        normalized = f"https://{normalized}"
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return None
    return normalized


def _normalize_text(value: str) -> str:
    return " ".join(html.unescape(value).split())


def _to_date(value: str | None):
    if not value:
        return None
    for pattern in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _matches_query(
    recruitment: PublicEmploymentRecruitmentSummary, query: str
) -> bool:
    normalized_query = query.casefold()
    searchable = " ".join(
        value
        for value in (
            recruitment.company,
            recruitment.title,
            recruitment.location,
            recruitment.employment_type,
            recruitment.recruitment_type,
        )
        if value
    ).casefold()
    return normalized_query in searchable
