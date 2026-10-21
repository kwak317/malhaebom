"""Public individual posting URL and source-owned HTML validation."""
from __future__ import annotations

import html
import json
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

EXTRA_SOURCES = {"rallit": "rallit.com", "wanted": "wanted.co.kr", "jumpit": "jumpit.saramin.co.kr"}


def extra_posting_key(url: str) -> tuple[str, str] | None:
    try:
        p = urlsplit(url)
        if p.scheme != "https" or p.username or p.password or p.port:
            return None
        for source, domain in EXTRA_SOURCES.items():
            hosts = {domain, f"www.{domain}"} if source != "jumpit" else {domain}
            path = {"rallit": r"/positions/([0-9]{1,12})(?:/[^/?#]+)?", "wanted": r"/wd/([0-9]{1,12})", "jumpit": r"/position/([0-9]{1,12})"}[source]
            match = re.fullmatch(path, p.path)
            if p.hostname in hosts and match:
                return source, match.group(1)
    except (ValueError, TypeError):
        pass
    return None


def canonical_extra_url(url: str) -> str:
    source, _ = extra_posting_key(url) or ("", "")
    domain = EXTRA_SOURCES[source]
    return f"https://{domain if source == 'jumpit' else 'www.' + domain}{urlsplit(url).path}"


class _PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}: self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.ignored: self.ignored -= 1

    def handle_data(self, text):
        if not self.ignored and text.strip(): self.parts.append(text.strip())


def _text(markup: str) -> str:
    parser = _PageText()
    parser.feed(markup)
    return " ".join(parser.parts)


def parse_extra_posting(source: str, posting_id: str, page: str, today: date):
    return parse_extra_posting_with_reason(source, posting_id, page, today)[0]


def parse_extra_posting_with_reason(source: str, posting_id: str, page: str, today: date):
    """Return parsed posting and a fixed reason; never include source content in diagnostics."""
    try:
        if source in {"rallit", "wanted"}:
            match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
            if not match: return None, "source_structure"
            props = json.loads(match.group(1))["props"]["pageProps"]
            data = props["position" if source == "rallit" else "initialData"]
            if str(data["id"]) != posting_id: return None, "posting_id_mismatch"
            if source == "rallit":
                if data["status"]["code"] != "HIRING": return None, "closed"
                levels = data["jobLevels"]
                if not any(level in levels for level in ("BEGINNER", "IRRELEVANT")): return None, "experience"
                company, title = data["companyName"], data["title"]
                deadline = None if data.get("isAlwaysHiring") is True else date.fromisoformat(data["endedAt"][:10])
                experience = "신입" if "BEGINNER" in levels else "경력무관"
                details = _text(" ".join(str(data.get(k) or "") for k in ("responsibilities", "basicQualifications", "preferredQualifications")))
            else:
                visible = _text(page)
                if data["status"] == "close" or "공고는 마감되었습니다" in visible: return None, "closed"
                if data["status"] != "active": return None, "application_unavailable"
                if data.get("hidden") is True or data.get("is_private") is True: return None, "application_unavailable"
                if data["career"].get("is_newbie") is not True: return None, "experience"
                company, title = data["company"]["company_name"], data["position"]
                close = data.get("close_time") or data.get("due_time")
                if not close and not any(word in visible for word in ("상시", "채용 시 마감")): return None, "deadline_missing"
                deadline = date.fromisoformat(close[:10]) if close else None
                experience = "신입"
                details = _text(" ".join(str(data.get(k) or "") for k in ("main_tasks", "requirements", "preferred_points")))
        else:
            visible = _text(page)
            if "마감된 포지션" in visible: return None, "closed"
            heading = re.search(r'<h1[^>]*>(.*?)</h1>', page, re.S)
            description = re.search(r'<meta[^>]*property="og:description"[^>]*content="([^"]+)"', page)
            experience_match = re.search(r'포지션 경력/학력/마감일/근무지역 정보\s+경력\s+(.+?)\s+학력', visible)
            deadline_match = re.search(r'마감일\s+(\d{4}-\d{2}-\d{2}|채용\s*시\s*마감|상시\s*채용)', visible)
            if not all((heading, description, experience_match, deadline_match)): return None, "source_structure"
            title = _text(heading.group(1))
            metadata = html.unescape(description.group(1))
            suffix = f" - {title} 채용"
            if not metadata.endswith(suffix): return None, "source_structure"
            company = metadata[:-len(suffix)]
            experience = experience_match.group(1).strip()
            if "신입제외" in re.sub(r"\s+", "", experience) or not any(word in experience for word in ("신입", "경력무관", "경력 무관")): return None, "experience"
            closing = deadline_match.group(1)
            deadline = date.fromisoformat(closing) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', closing) else None
            if "주요업무" not in visible or "자격요건" not in visible: return None, "details_missing"
            details = visible.split("주요업무", 1)[1].split("복지 및 혜택", 1)[0]
        if deadline is not None and deadline < today: return None, "deadline_expired"
        if not company or not title or len(details.strip()) < 20: return None, "details_missing"
        if not any(word in f"{title} {details}".casefold() for word in ("백엔드", "백앤드", "backend", "back-end", "서버 개발", "서버개발")): return None, "not_backend"
        return (company, title, deadline, experience, details[:20_000]), "verified"
    except (ValueError, KeyError, TypeError, AttributeError):
        return None, "source_structure"
