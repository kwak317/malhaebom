from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Any, Protocol
from urllib.parse import urlencode, urlparse

import httpx

from app.schemas.mofe_recruitment import (
    MofeRecruitmentSearchResponse,
    MofeRecruitmentSummary,
)


DEFAULT_MOFE_RECRUITMENT_API_URL = "https://apis.data.go.kr/1051000/recruitment/list"
OFFICIAL_MOFE_DATASET_URL = "https://www.data.go.kr/data/15125273/openapi.do"
_MOFE_API_HOST = "apis.data.go.kr"
_MOFE_API_PATH = "/1051000/recruitment/list"
_SEARCH_SAMPLE_SIZE = 100


class MofeRecruitmentUnavailable(RuntimeError):
    """재정경제부 공공기관 채용공시를 안전하게 조회할 수 없을 때 발생한다."""


class MofeRecruitmentHttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


class MofeRecruitmentSettings:
    def __init__(self, api_key: str, api_url: str) -> None:
        self.api_key = api_key
        self.api_url = api_url

    @classmethod
    def from_env(cls) -> "MofeRecruitmentSettings":
        api_key = os.getenv("MOFE_PUBLIC_INSTITUTION_JOB_API_KEY", "").strip()
        if not api_key:
            raise MofeRecruitmentUnavailable(
                "재정경제부 공공기관 채용정보 인증키가 설정되지 않았습니다."
            )

        api_url = (
            os.getenv("MOFE_PUBLIC_INSTITUTION_JOB_API_URL", "").strip()
            or DEFAULT_MOFE_RECRUITMENT_API_URL
        )
        parsed_url = urlparse(api_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != _MOFE_API_HOST
            or parsed_url.username
            or parsed_url.password
            or parsed_url.path != _MOFE_API_PATH
            or parsed_url.params
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise MofeRecruitmentUnavailable(
                "재정경제부 공공기관 채용정보 API URL 설정을 확인해 주세요."
            )
        return cls(api_key=api_key, api_url=api_url)


class MofeRecruitmentService:
    def __init__(
        self,
        settings: MofeRecruitmentSettings,
        http_client: MofeRecruitmentHttpClient | None = None,
    ) -> None:
        self.settings = settings
        self.http = http_client or httpx.Client(timeout=10.0)

    def search(
        self,
        *,
        query: str,
        page: int = 1,
        page_size: int = 10,
    ) -> MofeRecruitmentSearchResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("검색어를 입력해 주세요.")

        payload = self._request_json({
            "resultType": "json",
            "pageNo": str(page),
            # 제목·기관 키워드는 제공자 필터가 아니라 최신 공고 응답 범위에서 다시 찾는다.
            "numOfRows": str(max(page_size, _SEARCH_SAMPLE_SIZE)),
            "ongoingYn": "Y",
        })
        items = _result_items(payload)
        matched = [
            summary
            for item in items
            if (summary := _to_summary(item)) is not None
            and _matches_query(item, summary, normalized_query)
        ]
        return MofeRecruitmentSearchResponse(
            query=normalized_query,
            page=page,
            page_size=page_size,
            total_count=len(matched),
            recruitments=matched[:page_size],
        )

    def get_analysis_source(self, *, announcement_id: int) -> tuple[str, str]:
        # 이 제공자는 recrutPblntSn 조건을 무시하고 최신 일부 행을 반환한다.
        # 따라서 브라우저가 보낸 제목·기관명을 신뢰하지 않고, 목록 조회 때와 같은
        # 최신 진행 공고 범위를 서버에서 다시 받아 선택 ID를 찾는다.
        payload = self._request_json({
            "resultType": "json",
            "pageNo": "1",
            "numOfRows": str(_SEARCH_SAMPLE_SIZE),
            "ongoingYn": "Y",
        })
        item = next(
            (
                candidate
                for candidate in _result_items(payload)
                if _as_int(candidate.get("recrutPblntSn")) == announcement_id
            ),
            None,
        )
        if item is None:
            raise MofeRecruitmentUnavailable(
                "선택한 재정경제부 공공기관 채용공고 원문을 찾지 못했습니다."
            )
        source_text = _analysis_text(item)
        if len(source_text) < 20:
            raise MofeRecruitmentUnavailable(
                "공공기관 채용공고에서 분석할 텍스트를 찾지 못했습니다."
            )
        # 제공자가 http 원문 링크만 주는 경우에도, 실제 분석 근거는 서버가 재조회한
        # 공식 공공데이터 응답이다. 저장 링크는 HTTPS 공식 데이터셋으로 안전하게 고정한다.
        source_url = _safe_source_url(_text(item.get("srcUrl"))) or OFFICIAL_MOFE_DATASET_URL
        return source_text, source_url

    def _request_json(self, parameters: dict[str, str]) -> dict[str, Any]:
        # data.go.kr serviceKey는 환경 변수에 URL 인코딩된 문자열로 들어올 수 있다.
        # 키만 재인코딩하지 않고, 나머지 요청 파라미터만 URL 인코딩한다.
        url = f"{self.settings.api_url}?serviceKey={self.settings.api_key}&{urlencode(parameters)}"
        try:
            response = self.http.get(url, headers={"Accept": "application/json"})
        except httpx.HTTPError as error:
            raise MofeRecruitmentUnavailable(
                "재정경제부 공공기관 채용정보 검색에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
            ) from error
        if getattr(response, "status_code", None) != 200:
            raise MofeRecruitmentUnavailable(
                "재정경제부 공공기관 채용정보 검색에 실패했습니다. 잠시 후 다시 시도해 주세요."
            )
        try:
            payload = response.json()
        except (TypeError, ValueError) as error:
            raise MofeRecruitmentUnavailable(
                "재정경제부 공공기관 채용정보 응답을 처리하지 못했습니다."
            ) from error
        if not isinstance(payload, dict) or str(payload.get("resultCode")) != "200":
            raise MofeRecruitmentUnavailable(
                "재정경제부 공공기관 채용정보 검색에 실패했습니다. 잠시 후 다시 시도해 주세요."
            )
        return payload


class UnavailableMofeRecruitmentService:
    def __init__(self, message: str) -> None:
        self.message = message

    def search(self, **_: Any) -> MofeRecruitmentSearchResponse:
        raise MofeRecruitmentUnavailable(self.message)

    def get_analysis_source(self, **_: Any) -> tuple[str, str]:
        raise MofeRecruitmentUnavailable(self.message)


def _result_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("result")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _to_summary(item: dict[str, Any]) -> MofeRecruitmentSummary | None:
    announcement_id = _as_int(item.get("recrutPblntSn"))
    company = _text(item.get("instNm"))
    title = _text(item.get("recrutPbancTtl"))
    if announcement_id is None or not company or not title:
        return None
    return MofeRecruitmentSummary(
        announcement_id=announcement_id,
        company=company,
        title=title,
        source_url=_safe_source_url(_text(item.get("srcUrl"))),
        announced_at=_to_date(_text(item.get("pbancBgngYmd"))),
        deadline=_to_date(_text(item.get("pbancEndYmd"))),
        location=_text(item.get("workRgnNmLst")),
        employment_type=_text(item.get("hireTypeNmLst")),
        recruitment_type=_text(item.get("recrutSeNm")),
    )


def _analysis_text(item: dict[str, Any]) -> str:
    labels = (
        ("기관", "instNm"),
        ("공고 제목", "recrutPbancTtl"),
        ("직무", "ncsCdNmLst"),
        ("지원자격", "aplyQlfcCn"),
        ("우대사항", "prefCn"),
        ("우대조건", "prefCondCn"),
        ("결격사유", "disqlfcRsn"),
        ("전형절차", "scrnprcdrMthdExpln"),
    )
    return "\n\n".join(
        f"{label}: {value}"
        for label, field in labels
        if (value := _text(item.get(field)))
    )


def _matches_query(
    item: dict[str, Any],
    summary: MofeRecruitmentSummary,
    query: str,
) -> bool:
    searchable = " ".join(
        value
        for value in (
            summary.company,
            summary.title,
            summary.location,
            summary.employment_type,
            summary.recruitment_type,
            _text(item.get("ncsCdNmLst")),
            _text(item.get("aplyQlfcCn")),
        )
        if value
    ).casefold()
    return query.casefold() in searchable


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(html.unescape(value).split())
    return normalized or None


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _to_date(value: str | None):
    if not value:
        return None
    for pattern in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _safe_source_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return None
    return value.strip()
