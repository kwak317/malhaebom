from __future__ import annotations
from app.services.loading_progress import report_progress

import html
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urlsplit, urljoin
from zoneinfo import ZoneInfo

import httpx

from app.services.additional_job_sources import extra_posting_key, canonical_extra_url, parse_extra_posting_with_reason

from app.schemas.saramin_recommendation import (
    SaraminRecommendation,
    SaraminRecommendationRequest,
    SaraminRecommendationResponse,
)
from app.services.github_readme_analysis import GithubReadmeFetcher, readme_evidence_text
from app.services.ncs_competency import _REVIEWED_OPTIONS


SEARCH_MODEL = "google/gemini-3.8-flash"
SEARCH_MAX_TOKENS = 1536
_CREDITS_ERROR_MESSAGE = (
    "OpenRouter 계정 크레딧이 부족하거나 키 사용 한도에 도달했습니다. 계정 크레딧을 확인해 주세요."
)
_LOGGER = logging.getLogger(__name__)
_RETRYABLE_SEARCH_STATUSES = {408, 429, 500, 502, 503, 504}
_POSTING_PATHS = {"/zf_user/jobs/view", "/zf_user/jobs/relay/view"}
_BACKEND_WORDS = ("백엔드", "백앤드", "서버개발", "서버 개발", "backend", "back-end")
_NCS_WORDS = {
    "knowledge-foundations": ("네트워크", "미들웨어", "데이터베이스", "db", "server"),
    "knowledge-data": ("데이터", "database", "mysql", "postgresql", "db"),
    "knowledge-interface": ("인터페이스", "api", "rest"),
    "skill-server": ("서버", "백엔드", "backend", "spring", "api"),
    "skill-data": ("데이터", "database", "mysql", "postgresql", "db"),
    "skill-testing": ("테스트", "test", "결함", "qa"),
    "attitude-requirements": ("요구사항", "기획", "설계"),
    "attitude-improvement": ("개선", "리팩토링", "성능", "최적화"),
    "attitude-deployment": ("배포", "devops", "ci/cd", "운영"),
}
_FLOW_WORDS = ("인증", "조회", "저장", "생성", "처리", "결제", "api", "데이터", "배포", "테스트")


class SaraminRecommendationUnavailable(RuntimeError):
    pass


class SaraminRecommendationCreditsError(SaraminRecommendationUnavailable):
    pass


@dataclass(frozen=True)
class VerifiedPrivateJob:
    source: str
    posting_id: str
    company: str
    title: str
    source_url: str
    details: str


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]", "", value.casefold())


def _posting_deadline(metadata: str) -> date | None:
    field = re.search(r"마감일\s*:\s*([^,]+)", metadata)
    if field is None:
        raise ValueError("missing deadline")
    value = field.group(1).strip()
    if re.sub(r"\s+", "", value) == "채용시마감":
        return None
    dated = re.match(r"(\d{4})[-.](\d{2})[-.](\d{2})", value)
    if dated is None:
        raise ValueError("unrecognized deadline")
    return date(*(int(part) for part in dated.groups()))


def _posting_id(url: str) -> str | None:
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in {"saramin.co.kr", "www.saramin.co.kr"}
                or parsed.username or parsed.password or parsed.port or parsed.path not in _POSTING_PATHS):
            return None
        ids = parse_qs(parsed.query).get("rec_idx", [])
        if len(ids) != 1 or not re.fullmatch(r"[0-9]{1,12}", ids[0]):
            return None
        return ids[0]
    except ValueError:
        return None


def _jobkorea_id(url: str) -> str | None:
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in {"jobkorea.co.kr", "www.jobkorea.co.kr", "m.jobkorea.co.kr"}
                or parsed.username or parsed.password or parsed.port
                or not re.fullmatch(r"/Recruit/GI_Read/([0-9]{1,12})", parsed.path)):
            return None
        return parsed.path.rsplit("/", 1)[-1]
    except ValueError:
        return None


def _posting_key(url: str) -> tuple[str, str] | None:
    saramin_id = _posting_id(url)
    if saramin_id:
        return "saramin", saramin_id
    jobkorea_id = _jobkorea_id(url)
    return ("jobkorea", jobkorea_id) if jobkorea_id else extra_posting_key(url)


def _duplicate_job(left: SaraminRecommendation, right: SaraminRecommendation) -> bool:
    company = lambda value: _normalized(re.sub(r"(?:\(주\)|㈜|주식회사)", "", value.strip()))
    if company(left.company) != company(right.company):
        return False
    title = lambda value: _normalized(re.sub(r"(?:신입|경력|정규직|채용|모집)", "", value))
    left_title, right_title = title(left.title), title(right.title)
    return bool(left_title and right_title and SequenceMatcher(None, left_title, right_title).ratio() >= 0.9)


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored and data.strip():
            self.parts.append(data.strip())


class _SaraminDetailText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found = False
        self.depth = 0
        self.ignored = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div":
            if self.depth:
                self.depth += 1
            elif "user_content" in (dict(attrs).get("class") or "").split():
                self.found = True
                self.depth = 1
        if self.depth and tag in {"script", "style", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if self.depth and tag in {"script", "style", "noscript"} and self.ignored:
            self.ignored -= 1
        if self.depth and tag == "div":
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth and not self.ignored and data.strip():
            self.parts.append(data.strip())


def _saramin_details(page: str, visible: str) -> str:
    parser = _SaraminDetailText()
    parser.feed(page)
    if parser.found:
        return " ".join(parser.parts)[:20_000]
    details = visible.split("상세요강", 1)[-1].split("근무지위치", 1)[0]
    return details.split("본 기업은 구직자의", 1)[0].split("복리후생", 1)[0][:20_000]


class SaraminWebSearch:
    def __init__(self, api_key: str, http_client: Any | None = None) -> None:
        self.api_key = api_key
        self.http = http_client or httpx.Client(timeout=60.0, follow_redirects=False, trust_env=False)

    def _direct_posting_url(self, url: str) -> str | None:
        if _posting_key(url):
            return url
        try:
            parsed = urlsplit(url)
        except ValueError:
            return None
        if (parsed.scheme != "https" or parsed.hostname != "vertexaisearch.cloud.google.com"
                or not parsed.path.startswith("/grounding-api-redirect/")):
            return None
        try:
            response = self.http.get(url, timeout=8.0, follow_redirects=False)
            location = response.headers.get("location", "") if response.status_code in {301, 302, 303, 307, 308} else ""
            return location if _posting_key(location) else None
        except httpx.HTTPError:
            return None

    def _search_source(self, source: str, technologies: list[str], *, supplementary: bool = False) -> list[dict[str, str]]:
        first_technology = technologies[0] if technologies else "Spring Boot"
        second_technology = technologies[1] if len(technologies) > 1 else "서버 개발"
        today = datetime.now(ZoneInfo("Asia/Seoul"))
        this_month = today.strftime("%Y-%m")
        next_month = (today.replace(day=28) + timedelta(days=4)).strftime("%Y-%m")
        if source == "both":
            domain = "site:saramin.co.kr/zf_user/jobs/view OR site:jobkorea.co.kr/Recruit/GI_Read/"
        elif source == "saramin":
            domain = "site:saramin.co.kr/zf_user/jobs/view"
        else:
            domain = "site:jobkorea.co.kr/Recruit/GI_Read/"
        if source == "both":
            searches = (f'{domain} "백엔드" "신입"; '
                        f'{domain} "서버 개발" ("경력무관" OR "경력 무관")')
        elif supplementary:
            searches = (f'{domain} "{first_technology}" "신입"; '
                        f'{domain} "{second_technology}" "백엔드" ("경력무관" OR "경력 무관")')
        else:
            searches = (f'{domain} "백엔드" "신입"; '
                        f'{domain} "서버 개발" ("경력무관" OR "경력 무관")')
        try:
            request_body = {
                "model": SEARCH_MODEL,
                "temperature": 0,
                "reasoning": {"effort": "low"},
                "messages": [{"role": "user", "content": (
                    f"Today is {today.date()}. Search the live web for distinct individual "
                    f"{('Saramin or JobKorea' if source == 'both' else source)} backend or server developer "
                    "postings accepting junior or entry-level applicants "
                    "whose application deadline has not passed. "
                    f"Include postings closing this month and next month ({this_month}, {next_month}). "
                    "Also include active postings explicitly marked 채용 시 마감 (until filled). "
                    f"Use these two searches: {searches}. "
                    "Keep the response brief. Cite each individual job posting URL. "
                    "Exclude category and company-list pages."
                )}],
                "tools": [{"type": "openrouter:web_search", "parameters": (
                    {"engine": "exa", "max_uses": 1, "max_results": 20, "max_characters": 700,
                     "allowed_domains": ["saramin.co.kr", "jobkorea.co.kr"]}
                    if source == "both" else {"engine": "native", "max_uses": 2}
                )}],
                "max_tool_calls": 1 if source == "both" else 2,
                "max_tokens": 2048 if source == "both" else SEARCH_MAX_TOKENS,
            }
            for attempt in range(2):
                try:
                    response = self.http.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                        json=request_body,
                    )
                except (httpx.TimeoutException, httpx.ConnectError) as error:
                    _LOGGER.warning("Job web search transport failure: %s", type(error).__name__)
                    if attempt == 0:
                        continue
                    raise
                if response.status_code in _RETRYABLE_SEARCH_STATUSES and attempt == 0:
                    _LOGGER.warning("Job web search upstream HTTP %s; retrying once", response.status_code)
                    continue
                if response.status_code == 200:
                    choice = response.json()["choices"][0]
                    message = choice["message"]
                    if (not message.get("annotations")
                            and (choice.get("finish_reason") in {"length", "tool_calls"}
                                 or message.get("content", "") is None)):
                        _LOGGER.warning("Job web search response incomplete: %s", choice.get("finish_reason"))
                        if attempt == 0:
                            continue
                        raise SaraminRecommendationUnavailable(
                            "공고 검색 응답이 완료되지 않았습니다. 다시 시도해 주세요."
                        )
                break
            if response.status_code != 200:
                _LOGGER.warning("Job web search upstream HTTP %s", response.status_code)
                if response.status_code == 402:
                    raise SaraminRecommendationCreditsError(_CREDITS_ERROR_MESSAGE)
                raise SaraminRecommendationUnavailable("공고 검색에 연결하지 못했습니다. 다시 시도해 주세요.")
            message = response.json()["choices"][0]["message"]
            annotations = message.get("annotations", [])
            if not isinstance(annotations, list):
                raise ValueError("missing citations")
            cited_urls = [annotation["url_citation"] for annotation in annotations
                          if isinstance(annotation, dict) and annotation.get("type") == "url_citation"
                          and isinstance(annotation.get("url_citation"), dict)
                          and isinstance(annotation["url_citation"].get("url"), str)]
            citations: list[dict[str, str]] = []
            if not cited_urls:
                _LOGGER.warning("Job web search has no citations: source=%s supplementary=%s", source, supplementary)
                return citations
            with ThreadPoolExecutor(max_workers=min(6, len(cited_urls))) as executor:
                resolved_urls = executor.map(
                    self._direct_posting_url, (citation["url"] for citation in cited_urls)
                )
                for citation, direct_url in zip(cited_urls, resolved_urls):
                    if not direct_url or _posting_key(direct_url)[0] not in ("saramin", "jobkorea") or (source != "both" and _posting_key(direct_url)[0] != source):
                        continue
                    citations.append({
                        "url": direct_url,
                        "content": str(citation.get("content") or "")[:6000],
                    })
            return citations
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            _LOGGER.warning("Job web search response failure: %s", type(error).__name__)
            raise SaraminRecommendationUnavailable("공고 검색에 연결하지 못했습니다. 다시 시도해 주세요.") from error

    def search(self, technologies: list[str], *, supplementary: bool = False) -> list[dict[str, str]]:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [executor.submit(self._search_source, source, technologies, supplementary=supplementary)
                       for source in ("saramin", "jobkorea")]
            citations: list[dict[str, str]] = []
            failures = 0
            credit_failure = False
            for result in results:
                try:
                    citations.extend(result.result())
                except SaraminRecommendationCreditsError:
                    failures += 1
                    credit_failure = True
                except SaraminRecommendationUnavailable:
                    failures += 1
            if credit_failure and (failures == 2 or not citations):
                raise SaraminRecommendationCreditsError(_CREDITS_ERROR_MESSAGE)
            if failures == 2:
                raise SaraminRecommendationUnavailable("공고 검색에 연결하지 못했습니다. 다시 시도해 주세요.")
            return citations

    def search_more(self, technologies: list[str]) -> list[dict[str, str]]:
        return self.search(technologies, supplementary=True)

    def search_alternative(self, technologies: list[str]) -> list[dict[str, str]]:
        return self._search_source("both", technologies)


class SaraminPostingVerifier:
    def __init__(self, http_client: Any | None = None, *, timeout_seconds: float = 8.0) -> None:
        self.http = http_client or httpx.Client(timeout=timeout_seconds, follow_redirects=False, trust_env=False)

    def verify(self, source_url: str, *, today: datetime) -> tuple[str, str, str, date | None, str, str] | None:
        return self.verify_with_reason(source_url, today=today)[0]

    def verify_with_reason(self, source_url: str, *, today: datetime):
        posting_key = _posting_key(source_url)
        if posting_key is None:
            return None, "invalid_url"
        source, posting_id = posting_key
        if source in {"rallit", "wanted", "jumpit"}:
            canonical_url = canonical_extra_url(source_url)
            try:
                response = self.http.get(canonical_url, headers={"User-Agent": "Mozilla/5.0"})
                if source == "rallit" and response.status_code in {301, 302, 307, 308}:
                    redirected = urljoin(canonical_url, response.headers.get("location", ""))
                    if _posting_key(redirected) != posting_key or urlsplit(redirected).hostname != urlsplit(canonical_url).hostname or redirected == canonical_url:
                        return None, "unsafe_redirect"
                    canonical_url = canonical_extra_url(redirected)
                    response = self.http.get(canonical_url, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code != 200: return None, "http_status"
                if len(response.content) > 1_000_000: return None, "page_too_large"
                parsed, reason = parse_extra_posting_with_reason(source, posting_id, response.text, today.date())
                if parsed is None: return None, reason
                company, title, deadline, experience, details = parsed
                return (company, title, canonical_url, deadline, experience, details), "verified"
            except httpx.HTTPError:
                return None, "http_error"
        canonical_url = (f"https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={posting_id}"
                         if source == "saramin" else f"https://m.jobkorea.co.kr/Recruit/GI_Read/{posting_id}")
        try:
            response = self.http.get(canonical_url, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200: return None, "http_status"
            if len(response.content) > 1_000_000: return None, "page_too_large"
            page = response.text
            if "본 채용정보는 마감되었습니다" in page or "마감되었습니다." in page:
                return None, "closed"
            parser = _VisibleText()
            parser.feed(page)
            visible = " ".join(parser.parts)
            if source == "saramin":
                description = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', page)
                if not description:
                    return None, "source_structure"
                metadata = html.unescape(description.group(1))
                prefix, _, metadata_details = metadata.partition(", 경력:")
                company, separator, title = prefix.rpartition(", ")
                experience = metadata_details.split(",", 1)[0].strip()
                if not separator or not company or not title:
                    return None, "source_structure"
                deadline_date = _posting_deadline(metadata_details)
                details = _saramin_details(page, visible)
                if len(details.strip()) < 20:
                    return None, "details_missing"
            else:
                description = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', page)
                writer = re.search(r'<meta\s+name="writer"\s+content="([^"]+)"', page)
                heading = re.search(r"<title>([^<]+)</title>", page)
                if not description or not writer or not heading:
                    return None, "source_structure"
                metadata = html.unescape(description.group(1))
                company = html.unescape(writer.group(1)).strip()
                heading_text = html.unescape(heading.group(1))
                title_match = re.fullmatch(r".+? 채용 - (.+?) \| 잡코리아", heading_text)
                experience_match = re.search(r"경력\s*:\s*(.+?),\s*급여\s*:", metadata)
                if not title_match or not experience_match or not company:
                    return None, "source_structure"
                title = title_match.group(1).strip()
                deadline_date = _posting_deadline(metadata)
                experience = experience_match.group(1).strip()
                details = visible.split("모집요강", 1)[-1].split("접수기간", 1)[0].split("나와의 적합도", 1)[0][:20_000]
            if deadline_date is not None and deadline_date < today.date():
                return None, "deadline_expired"
            if not any(word in f"{title} {details}".casefold() for word in _BACKEND_WORDS):
                return None, "not_backend"
            if source == "jobkorea" and _normalized(experience) == "무관":
                experience = "경력무관"
            normalized_experience = _normalized(experience)
            if "신입제외" in normalized_experience or not any(word in normalized_experience for word in ("신입", "경력무관")):
                return None, "experience"
            return (company, title, canonical_url, deadline_date, experience, details), "verified"
        except httpx.HTTPError:
            return None, "http_error"
        except (UnicodeError, ValueError):
            return None, "source_structure"


class SaraminRecommendationService:
    def __init__(self, search: Any, verifier: SaraminPostingVerifier,
                 readme_fetcher: GithubReadmeFetcher | None = None) -> None:
        self.search = search
        self.verifier = verifier
        self.readme_fetcher = readme_fetcher or GithubReadmeFetcher()

    def verify_for_review(self, source_url: str) -> VerifiedPrivateJob:
        if _posting_key(source_url) is None:
            raise ValueError("지원되는 개별 공고 URL을 선택해 주세요.")
        verified = self.verifier.verify(
            source_url, today=datetime.now(ZoneInfo("Asia/Seoul"))
        )
        if verified is None:
            raise SaraminRecommendationUnavailable(
                "공고 원문에서 모집 상태·신입 조건 또는 분석할 상세 텍스트를 확인하지 못했습니다. "
                "상세가 이미지로 된 공고는 현재 분석할 수 없습니다. 다른 공고를 선택해 주세요."
            )
        company, title, canonical_url, _, _, details = verified
        if len(details.strip()) < 20:
            raise SaraminRecommendationUnavailable(
                "공고 원문에 분석할 직무·자격요건이 부족합니다. 다른 공고를 선택해 주세요."
            )
        source, posting_id = _posting_key(canonical_url) or ("", "")
        if not source:
            raise SaraminRecommendationUnavailable("공고 원문 주소를 확인하지 못했습니다.")
        return VerifiedPrivateJob(source, posting_id, company, title, canonical_url, details)

    def recommend(self, request: SaraminRecommendationRequest, *, confirmed_experience: list[dict] | None = None) -> SaraminRecommendationResponse:
        report_progress("선택한 역량과 프로젝트 검색 조건을 확인하고 있어요…")
        options = {row[0]: row[2] for row in _REVIEWED_OPTIONS}
        if len(set(request.selected_ncs_ids)) != len(request.selected_ncs_ids) or any(
            option not in options for option in request.selected_ncs_ids
        ):
            raise ValueError("선택한 NCS 역량을 확인해 주세요.")
        technologies: list[str] = []
        project_flows: list[str] = []
        if request.readme_analysis:
            analysis = request.readme_analysis
            markdown, sha, _ = self.readme_fetcher.fetch(analysis.source_url)
            source = readme_evidence_text(markdown)
            if sha != analysis.readme_sha or any(
                " ".join(item.source_excerpt.split()) not in source
                for item in (*analysis.technology_stack, *analysis.project_flow)
            ):
                raise ValueError("README 분석 근거가 현재 원문과 일치하지 않습니다. 다시 분석해 주세요.")
            technologies = [item.name for item in analysis.technology_stack
                            if _normalized(item.name) in _normalized(source)]
            project_flows = [item.source_excerpt for item in analysis.project_flow]
        resume_technologies = list(dict.fromkeys(
            fact.keyword for fact in request.resume_profile.facts
            if fact.category == "technology" and fact.keyword
        )) if request.resume_profile else []
        resume_flows = [fact.value for fact in request.resume_profile.facts
                        if fact.category == "project"] if request.resume_profile else []
        # Only the authenticated route supplies server-stored, explicitly confirmed facts.
        chat_values = list(dict.fromkeys(
            fact["value"] for item in (confirmed_experience or [])
            if item.get("user_confirmed") is True and item.get("source_type") == "user_chat"
            for fact in item.get("facts", [])
            if fact.get("kind") in {"technology", "responsibility", "project", "action", "outcome"}
            and isinstance(fact.get("value"), str)
        ))
        chat_technologies = list(dict.fromkeys(
            fact["value"] for item in (confirmed_experience or [])
            if item.get("user_confirmed") is True and item.get("source_type") == "user_chat"
            for fact in item.get("facts", []) if fact.get("kind") == "technology"
            and isinstance(fact.get("value"), str)
        ))
        chat_flows = list(dict.fromkeys(
            "API" if word == "api" else word for value in chat_values for word in _FLOW_WORDS
            if _normalized(word) in _normalized(value)
        ))
        search_technologies = list(dict.fromkeys([*technologies, *resume_technologies, *chat_technologies, *chat_flows]))
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        ranked: list[tuple[int, SaraminRecommendation]] = []
        seen: set[tuple[str, str]] = set()
        verified_count = 0
        audit: dict[str, dict[str, int]] = {}

        def count(source: str, reason: str) -> None:
            counts = audit.setdefault(source, {})
            counts[reason] = counts.get(reason, 0) + 1

        def verify_candidate(url: str):
            method = getattr(self.verifier, "verify_with_reason", None)
            if callable(method):
                verified, reason = method(url, today=now)
            else:
                verified = self.verifier.verify(url, today=now)
                reason = "verified" if verified else "unverified"
            return _posting_key(url)[0], verified, reason
        sources = getattr(self.search, "sources", ("saramin", "jobkorea"))

        def missing_sources() -> tuple[str, ...]:
            distinct: list[SaraminRecommendation] = []
            for _, candidate in ranked:
                if not any(_duplicate_job(candidate, item) for item in distinct):
                    distinct.append(candidate)
            return tuple(source for source in sources
                         if sum(_posting_key(item.source_url)[0] == source for item in distinct) < 5)

        def source_quotas_filled() -> bool:
            return not missing_sources()

        def collect(citations: list[dict[str, str]]) -> None:
            candidates: list[str] = []
            for citation in citations:
                posting_key = _posting_key(citation["url"])
                if not posting_key or posting_key[0] not in sources or posting_key in seen:
                    continue
                count(posting_key[0], "candidates")
                seen.add(posting_key)
                candidates.append(citation["url"])
            if not candidates:
                return
            report_progress("검색된 공고의 원문과 마감 여부를 검토하고 있어요…")
            if getattr(self.search, "return_when_ready", False):
                executor = ThreadPoolExecutor(max_workers=min(6, len(candidates)))
                pending = [executor.submit(verify_candidate, url) for url in candidates]
                try:
                    for future in as_completed(pending):
                        add_verified(future.result())
                        if source_quotas_filled():
                            break
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
                return
            with ThreadPoolExecutor(max_workers=min(6, len(candidates))) as executor:
                verified_jobs = executor.map(
                    verify_candidate, candidates
                )
                for verified in verified_jobs:
                    add_verified(verified)

        def add_verified(result) -> None:
            nonlocal verified_count
            source, verified, reason = result
            count(source, "checked")
            count(source, reason)
            if verified is None:
                return
            verified_count += 1
            company, title, url, deadline, experience, details = verified
            posting_text = f"{title} {details}"
            search_text = _normalized(posting_text)
            matched_technologies = [tech for tech in technologies if _normalized(tech) in search_text]
            matched_resume_technologies = [tech for tech in resume_technologies if _normalized(tech) in search_text]
            matched_resume_flows = list(dict.fromkeys(
                "API" if word == "api" else word
                for flow in resume_flows for word in _FLOW_WORDS
                if _normalized(word) in _normalized(flow) and _normalized(word) in search_text
            ))
            matched_flows = list(dict.fromkeys(
                "API" if word == "api" else word
                for flow in project_flows for word in _FLOW_WORDS
                if _normalized(word) in _normalized(flow) and _normalized(word) in search_text
            ))
            matched_chat_technologies = [tech for tech in chat_technologies if _normalized(tech) in search_text]
            matched_chat_flows = [word for word in chat_flows if _normalized(word) in search_text]
            matched_chat = list(dict.fromkeys([*matched_chat_technologies, *matched_chat_flows]))
            matched_ncs = [options[option_id] for option_id in request.selected_ncs_ids
                           if any(_normalized(word) in search_text for word in _NCS_WORDS[option_id])]
            if not matched_technologies and not matched_flows and not matched_ncs and not matched_resume_technologies and not matched_resume_flows and not matched_chat:
                count(source, "context_mismatch")
                return
            count(source, "matched")
            evidence_word = ((matched_technologies + matched_resume_technologies + matched_chat)[0] if matched_technologies or matched_resume_technologies or matched_chat else
                             next((word for option_id in request.selected_ncs_ids for word in _NCS_WORDS[option_id]
                                   if _normalized(word) in search_text), "백엔드"))
            match = re.search(re.escape(evidence_word), posting_text, re.IGNORECASE)
            excerpt = (posting_text[max(0, match.start() - 45):match.end() + 110]
                       if match else posting_text[:160])
            score = len(set(matched_technologies + matched_resume_technologies + matched_chat_technologies)) * 3 + len(set(matched_flows + matched_resume_flows + matched_chat_flows)) * 2 + len(matched_ncs)
            if "신입" in _normalized(experience) or "경력무관" in _normalized(experience):
                score += 3
            ranked.append((score, SaraminRecommendation(
                company=company, title=title, source_url=url, deadline=deadline,
                experience=experience, matched_technologies=matched_technologies[:3],
                matched_project_flows=matched_flows[:2],
                matched_ncs_labels=matched_ncs[:3], source_excerpt=excerpt,
                matched_resume_technologies=matched_resume_technologies[:3],
                matched_resume_project_flows=matched_resume_flows[:2],
                matched_chat_experience=matched_chat[:3],
            )))

        report_progress("채용공고 사이트에서 공고를 검색하고 있어요…")
        collect(self.search.search(search_technologies))
        search_error: SaraminRecommendationUnavailable | None = None
        alternative_searched = False
        if not ranked:
            search_alternative = getattr(self.search, "search_alternative", None)
            if callable(search_alternative):
                alternative_searched = True
                try:
                    report_progress("다른 검색 조건으로 공고를 추가 검색하고 있어요…")
                    collect(search_alternative(search_technologies))
                except SaraminRecommendationUnavailable as error:
                    search_error = error
        if not source_quotas_filled():
            search_more = getattr(self.search, "search_more", None)
            targeted_search_more = getattr(self.search, "search_more_for_sources", None)
            if callable(targeted_search_more) or callable(search_more):
                try:
                    if callable(targeted_search_more):
                        missing = missing_sources()
                        _LOGGER.info("Supplementary job search sources=%s", ",".join(missing))
                        report_progress("부족한 출처의 공고를 추가 검색하고 있어요…")
                        collect(targeted_search_more(search_technologies, missing))
                    else:
                        report_progress("공고를 추가 검색하고 있어요…")
                        collect(search_more(search_technologies))
                except SaraminRecommendationUnavailable as error:
                    search_error = error
                    _LOGGER.warning("Supplementary job search failed")
        if not source_quotas_filled() and not alternative_searched:
            search_alternative = getattr(self.search, "search_alternative", None)
            if callable(search_alternative):
                try:
                    report_progress("다른 검색 조건으로 공고를 추가 검색하고 있어요…")
                    collect(search_alternative(search_technologies))
                except SaraminRecommendationUnavailable:
                    if not ranked:
                        raise
        if not ranked and search_error is not None:
            raise search_error
        if not ranked:
            _LOGGER.warning(
                "Job recommendation search empty: candidates=%s verified=%s matched=0",
                len(seen), verified_count,
            )
        report_progress("검증된 공고와 지원 조건을 정리하고 있어요…")
        ranked.sort(key=lambda item: (-item[0], item[1].deadline or date.max, item[1].title))
        unique: list[SaraminRecommendation] = []
        for _, candidate in ranked:
            if not any(_duplicate_job(candidate, previous) for previous in unique):
                unique.append(candidate)
        selected: list[SaraminRecommendation] = []
        source_counts = {source: 0 for source in sources}
        for candidate in unique:
            source = _posting_key(candidate.source_url)[0]
            if source_counts[source] < 5:
                selected.append(candidate)
                source_counts[source] += 1
        for source in sources:
            _LOGGER.info("Job recommendation source=%s counts=%s selected=%s", source, audit.get(source, {}), source_counts[source])
        return SaraminRecommendationResponse(
            recommendations=selected, searched_at=now.isoformat()
        )


class UnavailableSaraminRecommendationService:
    def recommend(self, _: SaraminRecommendationRequest, *, confirmed_experience: list[dict] | None = None) -> SaraminRecommendationResponse:
        raise SaraminRecommendationUnavailable("OpenRouter API 키가 설정되지 않았습니다.")

    def verify_for_review(self, _: str) -> VerifiedPrivateJob:
        raise SaraminRecommendationUnavailable("공고 검토 서비스를 사용할 수 없습니다.")


def build_saramin_recommendation_service_from_env() -> (
    SaraminRecommendationService | UnavailableSaraminRecommendationService
):
    provider = os.getenv("JOB_SEARCH_PROVIDER", "web").strip().casefold() or "web"
    if provider in {"playmcp", "playmcp_tavily"}:
        from pathlib import Path
        from app.services.playmcp_job_search import PlayMcpSaraminSearch, PlayMcpTokenStore

        auth_file = os.getenv("PLAYMCP_AUTH_FILE", "/run/playmcp/auth.json").strip()
        bucket = os.getenv("PLAYMCP_AUTH_BUCKET", "").strip()
        if bucket:
            from app.services.playmcp_cloud_auth import CloudPlayMcpTokenStore, GcsAuthObject

            tokens: Any = CloudPlayMcpTokenStore(GcsAuthObject(bucket))
        else:
            tokens = PlayMcpTokenStore(Path(auth_file))
        search: Any = PlayMcpSaraminSearch(tokens)
        if provider == "playmcp_tavily":
            from app.services.tavily_job_search import PlayMcpTavilyJobSearch, TavilyJobKoreaSearch, TavilyAdditionalJobSearch

            tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
            if not tavily_key:
                raise ValueError("playmcp_tavily에는 TAVILY_API_KEY가 필요합니다.")
            search = PlayMcpTavilyJobSearch(search, TavilyJobKoreaSearch(tavily_key), tuple(
                TavilyAdditionalJobSearch(tavily_key, source) for source in ("rallit", "wanted", "jumpit")
            ))
        return SaraminRecommendationService(
            search,
            SaraminPostingVerifier(timeout_seconds=3.0),
        )
    if provider != "web":
        raise ValueError("JOB_SEARCH_PROVIDER는 web, playmcp 또는 playmcp_tavily여야 합니다.")
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return UnavailableSaraminRecommendationService()
    return SaraminRecommendationService(SaraminWebSearch(key), SaraminPostingVerifier())
