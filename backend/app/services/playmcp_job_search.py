from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.services.saramin_recommendation import SaraminRecommendationUnavailable, _posting_id


_LOGGER = logging.getLogger(__name__)
_GATEWAY = "https://playmcp.kakao.com/mcp"
_TOKEN_ENDPOINT = "https://playauth.kakao.com/playmcp/oauth2/token"
_SEARCH_TOOL = "SaraminMcp-search_saramin_jobs"
_AUTH_ERROR = "공고 검색 인증을 확인하지 못했습니다. PlayMCP 연결을 다시 확인해 주세요."
_SEARCH_ERROR = "공고 검색에 연결하지 못했습니다. 다시 시도해 주세요."


class PlayMcpTokenStore:
    """단일 API 프로세스가 사용하는 서버 전용 인증 파일."""

    def __init__(self, path: Path, http_client: Any | None = None) -> None:
        self.path = path
        self.http = http_client or httpx.Client(timeout=15.0, follow_redirects=False, trust_env=False)
        self.lock = threading.Lock()

    def access_token(self, *, refresh: bool = False) -> str:
        with self.lock:
            try:
                with self.path.open() as auth_file:
                    if os.fstat(auth_file.fileno()).st_mode & 0o7777 != 0o600:
                        raise PermissionError("unsafe authentication file permissions")
                    data = json.load(auth_file)
                token = data["access_token"]
                expires_at = float(data["expires_at"])
                if not isinstance(token, str) or not token.strip() or not math.isfinite(expires_at):
                    raise ValueError("invalid token")
                if refresh or expires_at <= time.time() + 60:
                    data = self._refresh(data)
                return data["access_token"]
            except Exception as error:
                _LOGGER.warning("PlayMCP authentication failure: %s", type(error).__name__)
                raise SaraminRecommendationUnavailable(_AUTH_ERROR) from None

    def _refresh(self, data: dict[str, Any]) -> dict[str, Any]:
        if not data.get("refresh_token") or not data.get("client_id"):
            raise ValueError("missing refresh credentials")
        response = self.http.post(_TOKEN_ENDPOINT, data={
            "grant_type": "refresh_token", "refresh_token": data["refresh_token"],
            "client_id": data["client_id"],
        })
        if response.status_code != 200:
            raise ValueError("refresh rejected")
        payload = response.json()
        token = payload["access_token"]
        lifetime = float(payload["expires_in"])
        if (not isinstance(token, str) or not token.strip() or
                not math.isfinite(lifetime) or lifetime <= 60):
            raise ValueError("invalid refreshed token")
        updated = {**data, "access_token": token, "expires_at": time.time() + lifetime,
                   "refresh_token": payload.get("refresh_token") or data["refresh_token"]}
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.path.parent, delete=False) as file:
                temporary = file.name
                os.chmod(temporary, 0o600)
                json.dump(updated, file)
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return updated


def _posting_urls(payload: dict[str, Any]) -> list[dict[str, str]]:
    if not isinstance(payload.get("widget"), dict):
        raise ValueError("missing search widget")
    found: dict[str, dict[str, str]] = {}
    junior_ids: set[str] = set()

    def text_values(node: Any) -> list[str]:
        if isinstance(node, list):
            return [value for child in node for value in text_values(child)]
        if not isinstance(node, dict):
            return []
        value = node.get("value")
        values = [value] if node.get("type") == "Text" and isinstance(value, str) else []
        return values + text_values(node.get("children", []))

    def visit(node: Any, junior: bool = False) -> None:
        if isinstance(node, list):
            for child in node:
                visit(child, junior)
        elif isinstance(node, dict):
            if node.get("type") == "Box":
                junior = junior or any("신입" in value or "".join(value.split()) == "경력무관"
                                       for value in text_values(node))
            action = node.get("onClickAction")
            if node.get("type") == "Button" and isinstance(action, dict) and action.get("type") == "apply":
                action_payload = action.get("payload")
                target = action_payload.get("target") if isinstance(action_payload, dict) else None
                url = target.get("url") if isinstance(target, dict) else None
                posting_id = _posting_id(url) if isinstance(url, str) else None
                if posting_id:
                    found[posting_id] = {
                        "url": f"https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={posting_id}",
                        "content": "",
                    }
                    if junior:
                        junior_ids.add(posting_id)
            visit(node.get("children", []), junior)

    visit(payload["widget"])
    return [found[key] for key in sorted(found, key=lambda key: key not in junior_ids)]


def _is_unauthorized(error: BaseException) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == 401
    return any(_is_unauthorized(child) for child in getattr(error, "exceptions", ()))


class PlayMcpSaraminSearch:
    sources = ("saramin",)
    return_when_ready = True

    def __init__(self, tokens: PlayMcpTokenStore, *, timeout_seconds: float = 8.0) -> None:
        self.tokens = tokens
        self.timeout_seconds = timeout_seconds

    def search(self, technologies: list[str]) -> list[dict[str, str]]:
        return self._search(page=1)

    def search_more(self, technologies: list[str]) -> list[dict[str, str]]:
        return self._search(page=2)

    def _search(self, *, page: int) -> list[dict[str, str]]:
        token = self.tokens.access_token()
        for attempt in range(2):
            try:
                payload = asyncio.run(asyncio.wait_for(
                    self._call_tool(token, page), timeout=self.timeout_seconds,
                ))
                return _posting_urls(payload)
            except Exception as error:
                if attempt == 0 and _is_unauthorized(error):
                    refresh_rejected = getattr(self.tokens, "refresh_after_rejection", None)
                    token = (refresh_rejected(token) if callable(refresh_rejected)
                             else self.tokens.access_token(refresh=True))
                    continue
                _LOGGER.warning("PlayMCP search failure: %s", type(error).__name__)
                message = _AUTH_ERROR if _is_unauthorized(error) else _SEARCH_ERROR
                raise SaraminRecommendationUnavailable(message) from None
        raise SaraminRecommendationUnavailable(_AUTH_ERROR)

    async def _call_tool(self, token: str, page: int) -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=self.timeout_seconds,
            follow_redirects=False, trust_env=False,
        ) as client:
            async with streamable_http_client(_GATEWAY, http_client=client) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(_SEARCH_TOOL, {"request": {
                        "searchWord": "백엔드", "page": page, "pageCount": 20, "sort": "Relation",
                        "companyType": [], "jobCategoryCodes": [], "locationCodes": [],
                        "maxCareer": 0, "minCareer": 0, "minSalary": 0, "recIds": "",
                        "subJobCategoryCodes": [], "subwayCodes": [],
                    }})
                    if result.isError:
                        raise ValueError("search tool rejected request")
                    if isinstance(result.structuredContent, dict) and "widget" in result.structuredContent:
                        return result.structuredContent
                    for content in result.content:
                        if content.type == "text":
                            payload = json.loads(content.text)
                            if isinstance(payload, dict) and "widget" in payload:
                                return payload
                    raise ValueError("unexpected search tool response")
