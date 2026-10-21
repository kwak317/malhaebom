from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx

from app.schemas.incheon_recruitment import (
    IncheonRecruitmentSearchResponse,
    IncheonRecruitmentSummary,
)


INCHEON_RECRUITMENT_API_URL = "https://www.incheon.go.kr/jobs/api/data/rcrut.do"
_MAX_SEARCH_PAGES = 10  # 제공자 API는 페이지당 10건만 반환하며 검색어 필터가 없다.


class IncheonRecruitmentUnavailable(RuntimeError):
    """인천 채용공고를 안전하게 조회할 수 없을 때 발생한다."""


class IncheonRecruitmentHttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


class IncheonRecruitmentSettings:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    @classmethod
    def from_env(cls) -> "IncheonRecruitmentSettings":
        api_key = os.getenv("INCHEON_RECRUITMENT_API_KEY", "").strip()
        if not api_key:
            raise IncheonRecruitmentUnavailable("인천 채용정보 인증키가 설정되지 않았습니다.")
        return cls(api_key)


class IncheonRecruitmentService:
    def __init__(
        self,
        settings: IncheonRecruitmentSettings,
        http_client: IncheonRecruitmentHttpClient | None = None,
    ) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=10.0)

    def search(
        self,
        *,
        query: str,
        page: int = 1,
        page_size: int = 10,
    ) -> IncheonRecruitmentSearchResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("검색어를 입력해 주세요.")

        matched: list[IncheonRecruitmentSummary] = []
        current_time = datetime.now(ZoneInfo("Asia/Seoul"))
        for provider_page in range(1, _MAX_SEARCH_PAGES + 1):
            payload = self._request_json(provider_page)
            data = payload.get("data")
            if not isinstance(data, dict) or not isinstance(data.get("list"), list):
                raise IncheonRecruitmentUnavailable("인천 채용정보 응답을 처리하지 못했습니다.")
            try:
                provider_total = int(data["count"])
            except (KeyError, TypeError, ValueError) as error:
                raise IncheonRecruitmentUnavailable("인천 채용정보 응답을 처리하지 못했습니다.") from error
            for item in data["list"]:
                if not isinstance(item, dict):
                    continue
                summary = _to_summary(item, current_time)
                if summary and normalized_query.casefold() in f"{summary.title} {summary.company}".casefold():
                    matched.append(summary)
            if provider_page * 10 >= provider_total or not data["list"]:
                break

        start = (page - 1) * page_size
        return IncheonRecruitmentSearchResponse(
            query=normalized_query,
            page=page,
            page_size=page_size,
            total_count=len(matched),
            recruitments=matched[start:start + page_size],
        )

    def _request_json(self, page: int) -> dict[str, Any]:
        try:
            response = self.http.get(
                INCHEON_RECRUITMENT_API_URL,
                params={"key": self.settings.api_key, "page": page},
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as error:
            raise IncheonRecruitmentUnavailable(
                "인천 채용정보 검색에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
            ) from error
        if getattr(response, "status_code", None) != 200:
            raise IncheonRecruitmentUnavailable(
                "인천 채용정보 검색에 실패했습니다. 잠시 후 다시 시도해 주세요."
            )
        try:
            payload = response.json()
        except (TypeError, ValueError) as error:
            raise IncheonRecruitmentUnavailable("인천 채용정보 응답을 처리하지 못했습니다.") from error
        if not isinstance(payload, dict) or payload.get("status") != "OK":
            raise IncheonRecruitmentUnavailable(
                "인천 채용정보 검색에 실패했습니다. 인증키와 API 상태를 확인해 주세요."
            )
        return payload


class UnavailableIncheonRecruitmentService:
    def __init__(self, message: str) -> None:
        self.message = message

    def search(self, **_: Any) -> IncheonRecruitmentSearchResponse:
        raise IncheonRecruitmentUnavailable(self.message)


def _to_summary(item: dict[str, Any], current_time: datetime) -> IncheonRecruitmentSummary | None:
    try:
        announcement_id = int(item.get("rcrut_info_sn"))
    except (TypeError, ValueError):
        return None
    company = _text(item.get("corp_nm"))
    title = _text(item.get("rcrut_ttl"))
    source_url = _safe_source_url(item.get("url"))
    if not company or not title or not source_url:
        return None
    deadline_text = _text(item.get("pbanc_end_dt"))
    try:
        deadline_time = datetime.strptime(deadline_text, "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("Asia/Seoul")
        ) if deadline_text else None
    except ValueError:
        deadline_time = None
    if deadline_time and deadline_time < current_time:
        return None
    announced_text = _text(item.get("pbanc_bgng_dt"))
    try:
        announced_time = datetime.strptime(announced_text, "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("Asia/Seoul")
        ) if announced_text else None
    except ValueError:
        announced_time = None
    if announced_time and announced_time > current_time:
        return None
    return IncheonRecruitmentSummary(
        announcement_id=announcement_id,
        company=company,
        title=title,
        source_url=source_url,
        announced_at=announced_time.date() if announced_time else None,
        deadline=deadline_time.date() if deadline_time else None,
        location=_text(item.get("powk_addr")),
        employment_type=_text(item.get("work_type_nm")),
        recruitment_type=_text(item.get("crr_se_nm")),
    )


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(html.unescape(value).split())
    return normalized or None


def _safe_source_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.incheon.go.kr"
        or parsed.username
        or parsed.password
        or not parsed.path.startswith("/jobs/main/recruit/")
        or not parsed.path.endswith("/view.do")
    ):
        return None
    return value.strip()
