"""Bounded discovery from the public listings used by each recruitment website."""
from __future__ import annotations

import logging

import httpx

_LOGGER = logging.getLogger(__name__)
_ENDPOINTS = {
    "rallit": "https://www.rallit.com/client/api/v1/position",
    "wanted": "https://www.wanted.co.kr/api/chaos/search/v1/position",
    "jumpit": "https://jumpit-api.saramin.co.kr/api/positions",
}


def search_public_catalog(source: str, http) -> list[dict[str, str]]:
    found: dict[int, dict[str, str]] = {}
    for page in (1, 2):
        params = {
            "rallit": {"pageNumber": page, "pageSize": 100},
            "wanted": {"query": "백엔드", "years": "0", "sort": "job.latest_order", "country": "kr", "limit": 30, "offset": (page - 1) * 30},
            "jumpit": {"jobCategory": 1, "career": 0, "sort": "reg_dt", "page": page},
        }[source]
        try:
            response = http.get(_ENDPOINTS[source], params=params, timeout=8.0)
            response.raise_for_status()
            if len(response.content) > 1_000_000: raise ValueError("catalog too large")
            payload = response.json()
            rows = payload["data"]["items"] if source == "rallit" else payload["data"] if source == "wanted" else payload["result"]["positions"]
            if not isinstance(rows, list): raise ValueError("invalid catalog rows")
            for row in rows:
                if not isinstance(row, dict): continue
                posting_id = row.get("id")
                if type(posting_id) is not int or not 0 < posting_id < 10**12: continue
                if source == "rallit":
                    levels = row.get("jobLevels", [])
                    title = str(row.get("title") or "").casefold()
                    if row.get("status", {}).get("code") != "HIRING" or not isinstance(levels, list): continue
                    if not any(level in levels for level in ("BEGINNER", "IRRELEVANT")): continue
                    if not any(word in title for word in ("백엔드", "백앤드", "backend", "back-end", "서버")): continue
                    url = f"https://www.rallit.com/positions/{posting_id}"
                elif source == "wanted":
                    if row.get("annual_from") != 0 or type(row.get("annual_from")) is not int: continue
                    url = f"https://www.wanted.co.kr/wd/{posting_id}"
                else:
                    if row.get("newcomer") is not True: continue
                    url = f"https://jumpit.saramin.co.kr/position/{posting_id}"
                found.setdefault(posting_id, {"url": url, "content": ""})
                if len(found) >= 20: break
            _LOGGER.info("Job catalog source=%s page=%s raw=%s candidates=%s", source, page, len(rows), len(found))
            if len(found) >= 20 or not rows: break
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as error:
            _LOGGER.warning("Job catalog source=%s failure=%s", source, type(error).__name__)
            break
    return list(found.values())
