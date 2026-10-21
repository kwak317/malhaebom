from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.saramin_recommendation import SaraminRecommendationRequest
from app.services.playmcp_job_search import PlayMcpSaraminSearch, PlayMcpTokenStore, _posting_urls
from app.services.saramin_recommendation import (
    SaraminRecommendationService, SaraminRecommendationUnavailable, SaraminWebSearch,
    build_saramin_recommendation_service_from_env,
)


def cards(*urls):
    return {"widget": {"type": "Col", "children": [
        {"type": "Button", "onClickAction": {"type": "apply", "payload": {
            "target": {"url": url},
        }}} for url in urls
    ]}}


class PlayMcpJobSearchTest(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "auth.json"
        self.credentials = {"access_token": "access-secret", "refresh_token": "refresh-secret",
                            "expires_at": time.time() + 3600, "client_id": "test-client"}
        self.write_credentials()
        self.tokens = PlayMcpTokenStore(self.path)
        self.auth_file_mode = 0o600
        self.fstat_patch = patch(
            "app.services.playmcp_job_search.os.fstat",
            side_effect=lambda _: SimpleNamespace(st_mode=self.auth_file_mode),
        )
        self.fstat_patch.start()
        self.addCleanup(self.fstat_patch.stop)


    def write_credentials(self):
        self.path.write_text(json.dumps(self.credentials))
        self.path.chmod(0o600)


    def test_only_individual_saramin_apply_links_are_used_and_deduplicated(self):
        response = cards(
            "https://saramin.co.kr/zf_user/jobs/relay/view?rec_idx=123&utm_source=kakao",
            "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123",
            "https://evil.example/zf_user/jobs/view?rec_idx=124",
            "https://www.saramin.co.kr/zf_user/search?rec_idx=125",
            "https://user:password@www.saramin.co.kr/zf_user/jobs/view?rec_idx=126",
            "http://www.saramin.co.kr/zf_user/jobs/view?rec_idx=127",
        )
        response["widget"]["children"].append({"type": "Button", "onClickAction": {
            "type": "jobs.view_more", "payload": {"target": {
                "url": "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=128",
            }},
        }})
        self.assertEqual(_posting_urls(response), [{
            "url": "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123", "content": "",
        }])


    def test_empty_widget_is_empty_result_but_missing_widget_is_failure(self):
        self.assertEqual(_posting_urls(cards()), [])
        with self.assertRaises(ValueError):
            _posting_urls({"copy_text": "not a search result"})


    def test_valid_token_does_not_refresh(self):
        with patch.object(self.tokens.http, "post") as post:
            self.assertEqual(self.tokens.access_token(), "access-secret")
            post.assert_not_called()


    def test_insecure_auth_file_is_rejected_before_read_or_refresh(self):
        for mode in (0o644, 0o640, 0o660):
            with self.subTest(mode=oct(mode)):
                self.auth_file_mode = mode
                with patch("app.services.playmcp_job_search.json.load") as read, \
                        patch.object(self.tokens.http, "post") as post:
                    for refresh in (False, True):
                        with self.assertRaises(SaraminRecommendationUnavailable) as caught:
                            self.tokens.access_token(refresh=refresh)
                    read.assert_not_called()
                    post.assert_not_called()
                self.assertEqual(self.auth_file_mode, mode)
                self.assertNotIn("access-secret", str(caught.exception))
                self.assertNotIn("refresh-secret", str(caught.exception))
        self.auth_file_mode = 0o600


    def test_expired_token_refresh_is_persisted_with_restricted_permissions(self):
        self.credentials["expires_at"] = time.time() - 1
        self.write_credentials()
        response = SimpleNamespace(status_code=200, json=lambda: {
            "access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 43200,
        })
        with (
            patch.object(self.tokens.http, "post", return_value=response) as post,
            patch("app.services.playmcp_job_search.os.chmod", wraps=os.chmod) as chmod,
        ):
            self.assertEqual(self.tokens.access_token(), "new-access")
            self.assertEqual(self.tokens.access_token(), "new-access")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(chmod.call_args.args[1], 0o600)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved["refresh_token"], "new-refresh")
        self.assertGreater(saved["expires_at"], time.time() + 43100)


    def test_missing_or_invalid_credentials_fail_without_exposing_secrets(self):
        for value in ["{", "[]", '{"access_token":"access-secret"}',
                      '{"access_token":"access-secret","expires_at":"NaN"}']:
            self.path.write_text(value)
            with self.assertRaises(SaraminRecommendationUnavailable) as caught:
                self.tokens.access_token()
            self.assertNotIn("access-secret", str(caught.exception))
        with self.assertRaises(SaraminRecommendationUnavailable):
            PlayMcpTokenStore(self.path.parent / "missing.json").access_token()


    def test_refresh_rejection_preserves_auth_file_and_does_not_expose_response(self):
        self.credentials["expires_at"] = 0
        self.write_credentials()
        before = self.path.read_bytes()
        with patch.object(self.tokens.http, "post", return_value=SimpleNamespace(status_code=400)):
            with self.assertRaises(SaraminRecommendationUnavailable) as caught:
                self.tokens.access_token()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn("refresh-secret", str(caught.exception))


    def test_junior_card_labels_only_prioritize_urls_without_accepting_or_dropping_jobs(self):
        urls = [f"https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={n}" for n in range(1, 4)]
        response = {"widget": {"type": "Col", "children": [
            {"type": "Box", "children": [{"type": "Text", "value": label},
                                          cards(url)["widget"]["children"][0]]}
            for url, label in zip(urls, ["경력", "경력 무관", "신입/경력"])
        ]}}
        self.assertEqual([item["url"] for item in _posting_urls(response)], [urls[1], urls[2], urls[0]])

    def test_mcp_pages_and_timeout_failure_never_call_web_search(self):
        search = PlayMcpSaraminSearch(self.tokens, timeout_seconds=0.01)
        with patch.object(search, "_call_tool", new=AsyncMock(return_value=cards())) as call:
            search.search(["Spring Boot"])
            search.search_more(["Spring Boot"])
            self.assertEqual([item.args[1] for item in call.call_args_list], [1, 2])
        async def slow(*_):
            await asyncio.sleep(1)
        with patch.object(search, "_call_tool", new=slow), patch.object(SaraminWebSearch, "search") as web:
            with self.assertRaises(SaraminRecommendationUnavailable):
                search.search([])
            web.assert_not_called()

    def test_401_refreshes_once_and_retries_then_fails_safely(self):
        request = httpx.Request("POST", "https://playmcp.kakao.com/mcp")
        unauthorized = httpx.HTTPStatusError("remote access-secret", request=request,
                                            response=httpx.Response(401, request=request))
        search = PlayMcpSaraminSearch(self.tokens)
        with patch.object(self.tokens, "access_token", side_effect=["old", "new"]) as token:
            with patch.object(search, "_call_tool", new=AsyncMock(side_effect=[unauthorized, cards()])) as call:
                self.assertEqual(search.search([]), [])
                token.assert_called_with(refresh=True)
                self.assertEqual(call.call_count, 2)
        with patch.object(self.tokens, "access_token", return_value="old"):
            with patch.object(search, "_call_tool", new=AsyncMock(side_effect=unauthorized)) as call:
                with self.assertRaises(SaraminRecommendationUnavailable) as caught:
                    search.search([])
                self.assertEqual(call.call_count, 2)
                self.assertNotIn("access-secret", str(caught.exception))

    def test_actual_sdk_call_uses_fixed_tool_and_does_not_send_user_context(self):
        class Context:
            def __init__(self, value): self.value = value
            async def __aenter__(self): return self.value
            async def __aexit__(self, *_): pass
        result = SimpleNamespace(isError=False, structuredContent=None, content=[
            SimpleNamespace(type="text", text=json.dumps(cards())),
        ])
        session = SimpleNamespace(initialize=AsyncMock(), call_tool=AsyncMock(return_value=result))
        with patch("app.services.playmcp_job_search.streamable_http_client", return_value=Context((None, None, None))):
            with patch("app.services.playmcp_job_search.ClientSession", return_value=Context(session)):
                self.assertEqual(asyncio.run(PlayMcpSaraminSearch(self.tokens)._call_tool("access", 1)), cards())
        session.call_tool.assert_awaited_once_with("SaraminMcp-search_saramin_jobs", {"request": {
            "searchWord": "백엔드", "page": 1, "pageCount": 20, "sort": "Relation",
            "companyType": [], "jobCategoryCodes": [], "locationCodes": [],
            "maxCareer": 0, "minCareer": 0, "minSalary": 0, "recIds": "",
            "subJobCategoryCodes": [], "subwayCodes": [],
        }})

    def test_five_verified_saramin_jobs_do_not_trigger_a_second_source_search(self):
        search = PlayMcpSaraminSearch(self.tokens)
        verifier = SimpleNamespace(verify=lambda url, today: (
            "회사" + url.rsplit("=", 1)[-1], "백엔드 개발자", url, today.date(), "경력 무관", "API 서버 개발",
        ))
        urls = [f"https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={n}" for n in range(1, 6)]
        with patch.object(search, "_call_tool", new=AsyncMock(return_value=cards(*urls))) as call:
            result = SaraminRecommendationService(search, verifier).recommend(
                SaraminRecommendationRequest(selected_ncs_ids=["skill-server"]),
            )
        self.assertEqual(len(result.recommendations), 5)
        self.assertEqual(call.call_count, 1)

    def test_provider_can_switch_back_and_playmcp_does_not_need_openrouter_key(self):
        with patch.dict(os.environ, {"JOB_SEARCH_PROVIDER": "playmcp", "OPENROUTER_API_KEY": "",
                                    "PLAYMCP_AUTH_FILE": str(self.path)}):
            service = build_saramin_recommendation_service_from_env()
            self.assertIsInstance(service.search, PlayMcpSaraminSearch)
            self.assertEqual(service.verifier.http.timeout.read, 3.0)
        with patch.dict(os.environ, {"JOB_SEARCH_PROVIDER": "web", "OPENROUTER_API_KEY": "test"}):
            self.assertIsInstance(build_saramin_recommendation_service_from_env().search, SaraminWebSearch)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test"}):
            os.environ.pop("JOB_SEARCH_PROVIDER", None)
            self.assertIsInstance(build_saramin_recommendation_service_from_env().search, SaraminWebSearch)

    def test_ready_matches_return_without_waiting_for_a_slow_first_candidate(self):
        release = threading.Event()
        slow_finished = threading.Event()
        def verify(url, today):
            if url.endswith("=1"):
                release.wait(2)
                slow_finished.set()
            return ("회사" + url.rsplit("=", 1)[-1], "백엔드 개발자", url,
                    today.date(), "신입", "API 서버 개발")
        search = PlayMcpSaraminSearch(self.tokens)
        urls = [f"https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={n}" for n in range(1, 7)]
        service = SaraminRecommendationService(search, SimpleNamespace(verify=verify))
        try:
            with patch.object(search, "_call_tool", new=AsyncMock(return_value=cards(*urls))):
                result = service.recommend(SaraminRecommendationRequest(selected_ncs_ids=["skill-server"]))
            self.assertFalse(slow_finished.is_set())
            self.assertEqual(len(result.recommendations), 5)
            self.assertNotIn(urls[0], [item.source_url for item in result.recommendations])
        finally:
            release.set()

    def test_unverified_duplicate_and_unmatched_candidates_do_not_fill_fast_results(self):
        def verify(url, today):
            posting_id = int(url.rsplit("=", 1)[-1])
            if posting_id == 1:
                return None
            if posting_id == 2:
                return ("다른 회사", "업무", url, today.date(), "신입", "관련 없는 내용")
            company = "중복 회사" if posting_id in {3, 4} else str(posting_id)
            return (company, "백엔드 개발자", url, today.date(), "신입", "API 서버 개발")
        search = PlayMcpSaraminSearch(self.tokens)
        urls = [f"https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={n}" for n in range(1, 9)]
        with patch.object(search, "_call_tool", new=AsyncMock(return_value=cards(*urls))) as call:
            result = SaraminRecommendationService(search, SimpleNamespace(verify=verify)).recommend(
                SaraminRecommendationRequest(selected_ncs_ids=["skill-server"]),
            )
        self.assertEqual(len(result.recommendations), 5)
        self.assertEqual(len({item.company for item in result.recommendations}), 5)
        self.assertFalse({urls[0], urls[1]} & {item.source_url for item in result.recommendations})
        self.assertEqual(call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
