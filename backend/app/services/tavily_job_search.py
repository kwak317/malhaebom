from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from app.services.public_job_catalog import search_public_catalog
from app.services.additional_job_sources import EXTRA_SOURCES, canonical_extra_url
from app.services.saramin_recommendation import SaraminRecommendationUnavailable, _posting_key


_LOGGER = logging.getLogger(__name__)
_SEARCH_URL = "https://api.tavily.com/search"
_PATHS = {"jobkorea": "/Recruit/GI_Read/", "rallit": "/positions/", "wanted": "/wd/", "jumpit": "/position/"}


def _discovery_query(source: str, *, recent: bool = False) -> str:
    domain = "jobkorea.co.kr" if source == "jobkorea" else EXTRA_SOURCES[source]
    query = f"site:{domain}{_PATHS[source]} 백엔드 서버 개발자 신입 경력무관 채용"
    if recent:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
        query = f'site:{domain}{_PATHS[source]} "신입" "백엔드" 채용 {now.year} {now.month}월'
    return query


_SEARCH_ERROR = "공고 검색에 연결하지 못했습니다. 다시 시도해 주세요."


class TavilyJobKoreaSearch:
    """Find JobKorea posting URLs; the existing verifier checks their live content."""

    def __init__(self, api_key: str, http_client: Any | None = None) -> None:
        self.api_key = api_key
        self.http = http_client or httpx.Client(timeout=8.0, follow_redirects=False, trust_env=False)

    def search(self, _technologies: list[str]) -> list[dict[str, str]]:
        return self._search_query(_discovery_query("jobkorea"))

    def search_more(self, _technologies: list[str]) -> list[dict[str, str]]:
        queries = (
            _discovery_query("jobkorea", recent=True),
            "site:jobkorea.co.kr/Recruit/GI_Read/ 서버 개발자 신입 경력무관 Python Node.js",
        )
        found: dict[str, dict[str, str]] = {}
        failures = 0
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(self._search_query, query, recent=(index == 0)) for index, query in enumerate(queries)]
            for future in futures:
                try:
                    for row in future.result():
                        found.setdefault(row["url"], row)
                except SaraminRecommendationUnavailable:
                    failures += 1
        if failures == len(queries):
            raise SaraminRecommendationUnavailable(_SEARCH_ERROR)
        return list(found.values())

    def _search_query(self, query: str, *, recent: bool = False) -> list[dict[str, str]]:
        try:
            response = self.http.post(
                _SEARCH_URL,
                timeout=20.0 if recent else 8.0,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "query": query,
                    "search_depth": "advanced" if recent else "basic",
                    "max_results": 10,
                    **({"time_range": "month"} if recent else {}),
                    "include_domains": ["jobkorea.co.kr"],
                    "include_domains_mode": "restrict",
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
            results = payload["results"]
            if not isinstance(results, list):
                raise ValueError("invalid search results")
            found: dict[str, dict[str, str]] = {}
            for item in results:
                url = item.get("url") if isinstance(item, dict) else None
                key = _posting_key(url) if isinstance(url, str) else None
                if key and key[0] == "jobkorea":
                    found.setdefault(key[1], {
                        "url": f"https://m.jobkorea.co.kr/Recruit/GI_Read/{key[1]}", "content": "",
                    })
            _LOGGER.info("Job discovery source=jobkorea raw=%s individual=%s", len(results), len(found))
            return list(found.values())
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            _LOGGER.warning("Tavily job search failure: %s", type(error).__name__)
            raise SaraminRecommendationUnavailable(_SEARCH_ERROR) from None


class TavilyAdditionalJobSearch(TavilyJobKoreaSearch):
    def __init__(self, api_key: str, source: str, http_client: Any | None = None):
        super().__init__(api_key, http_client)
        self.source = source

    def search(self, _technologies: list[str]) -> list[dict[str, str]]:
        with ThreadPoolExecutor(max_workers=2) as executor:
            catalog = executor.submit(search_public_catalog, self.source, self.http)
            web = executor.submit(self._search_query, _discovery_query(self.source))
            rows = catalog.result()
            try:
                rows += web.result()
            except SaraminRecommendationUnavailable:
                if not rows: raise
        found = {}
        for row in rows:
            key = _posting_key(row["url"])
            if key and key[0] == self.source:
                found.setdefault(key, row)
        return list(found.values())

    def search_more(self, _technologies: list[str]) -> list[dict[str, str]]:
        return self._search_query(_discovery_query(self.source, recent=True), recent=True)

    def _search_query(self, query: str, *, recent: bool = False) -> list[dict[str, str]]:
        try:
            response = self.http.post(_SEARCH_URL, timeout=20.0 if recent else 8.0, headers={"Authorization": f"Bearer {self.api_key}"}, json={
                "query": query, "search_depth": "advanced" if recent else "basic", "max_results": 10,
                **({"time_range": "month"} if recent else {}),
                "include_domains": [EXTRA_SOURCES[self.source]], "include_domains_mode": "restrict",
                "include_answer": False, "include_raw_content": False,
            })
            response.raise_for_status()
            rows = response.json()["results"]
            if not isinstance(rows, list): raise ValueError("invalid search results")
            found = {}
            for row in rows:
                url = row.get("url") if isinstance(row, dict) else None
                key = _posting_key(url) if isinstance(url, str) else None
                if key and key[0] == self.source:
                    found.setdefault(key[1], {"url": canonical_extra_url(url), "content": ""})
            _LOGGER.info("Job discovery source=%s raw=%s individual=%s", self.source, len(rows), len(found))
            return list(found.values())
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            _LOGGER.warning("Job discovery source=%s failure=%s", self.source, type(error).__name__)
            raise SaraminRecommendationUnavailable(_SEARCH_ERROR) from None


class PlayMcpTavilyJobSearch:
    sources = ("saramin", "jobkorea")
    return_when_ready = True

    def __init__(self, saramin_search: Any, jobkorea_search: TavilyJobKoreaSearch, additional_searches: tuple[Any, ...] = ()) -> None:
        self.saramin_search = saramin_search
        self.jobkorea_search = jobkorea_search
        self.additional_searches = additional_searches
        self.sources = ("saramin", "jobkorea", *(provider.source for provider in additional_searches))

    def search(self, technologies: list[str]) -> list[dict[str, str]]:
        with ThreadPoolExecutor(max_workers=2 + len(self.additional_searches)) as executor:
            searches = [executor.submit(provider.search, technologies) for provider in (self.saramin_search, self.jobkorea_search, *self.additional_searches)]
            candidates: list[dict[str, str]] = []
            failures = 0
            for future in searches:
                try:
                    candidates.extend(future.result())
                except SaraminRecommendationUnavailable:
                    failures += 1
            if failures == len(searches):
                raise SaraminRecommendationUnavailable(_SEARCH_ERROR)
            return candidates

    def search_more(self, technologies: list[str]) -> list[dict[str, str]]:
        return self.search_more_for_sources(technologies, self.sources)

    def search_more_for_sources(self, technologies: list[str], sources: tuple[str, ...]) -> list[dict[str, str]]:
        with ThreadPoolExecutor(max_workers=min(5, len(self.sources))) as executor:
            futures = []
            for source, provider in zip(self.sources, (self.saramin_search, self.jobkorea_search, *self.additional_searches)):
                if source not in sources:
                    continue
                search_more = getattr(provider, "search_more", None)
                if callable(search_more):
                    futures.append(executor.submit(search_more, technologies))
            candidates: dict[str, dict[str, str]] = {}
            failures = 0
            for future in futures:
                try:
                    for row in future.result():
                        candidates.setdefault(row["url"], row)
                except SaraminRecommendationUnavailable:
                    failures += 1
            if futures and failures == len(futures):
                raise SaraminRecommendationUnavailable(_SEARCH_ERROR)
            return list(candidates.values())
