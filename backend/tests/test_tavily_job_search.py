from __future__ import annotations

import json
import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.saramin_recommendation import SaraminRecommendationRequest
from app.services.saramin_recommendation import (
    SaraminRecommendationService,
    SaraminRecommendationUnavailable,
    build_saramin_recommendation_service_from_env,
)
from app.services.tavily_job_search import PlayMcpTavilyJobSearch, TavilyJobKoreaSearch


SARAMIN = "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={}"
JOBKOREA = "https://m.jobkorea.co.kr/Recruit/GI_Read/{}"


class TavilyJobSearchTest(unittest.TestCase):
    def test_search_sends_fixed_query_and_keeps_only_individual_jobkorea_urls(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"results": [
                {"url": "https://www.jobkorea.co.kr/Recruit/GI_Read/123?tracking=1", "content": "unverified"},
                {"url": "https://m.jobkorea.co.kr/Recruit/GI_Read/123"},
                {"url": "https://www.jobkorea.co.kr/Recruit/Home"},
                {"url": "https://evil.example/Recruit/GI_Read/999"},
                {"url": "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=77"},
            ]})

        http = httpx.Client(transport=httpx.MockTransport(respond))
        result = TavilyJobKoreaSearch("test-key", http).search(["private README technology"])
        self.assertEqual(result, [{"url": JOBKOREA.format(123), "content": ""}])
        body = json.loads(requests[0].content)
        self.assertEqual(requests[0].url, "https://api.tavily.com/search")
        self.assertEqual(requests[0].headers["Authorization"], "Bearer test-key")
        self.assertEqual(body["include_domains"], ["jobkorea.co.kr"])
        self.assertNotIn("private README technology", str(body))

    def test_tavily_failure_and_bad_shape_are_safe(self):
        for response in (httpx.Response(401, text="secret-response"), httpx.Response(200, json={"results": {}})):
            with self.subTest(status=response.status_code):
                http = httpx.Client(transport=httpx.MockTransport(lambda _: response))
                with self.assertRaises(SaraminRecommendationUnavailable) as caught:
                    TavilyJobKoreaSearch("secret-key", http).search([])
                self.assertNotIn("secret", str(caught.exception))

    def test_combined_search_keeps_both_sources_and_survives_one_failure(self):
        saramin = SimpleNamespace(
            search=lambda _: [{"url": SARAMIN.format(1), "content": ""}],
            search_more=lambda _: [],
        )
        jobkorea = SimpleNamespace(search=lambda _: [{"url": JOBKOREA.format(2), "content": ""}])
        combined = PlayMcpTavilyJobSearch(saramin, jobkorea)
        self.assertEqual(len(combined.search([])), 2)

        def unavailable(_):
            raise SaraminRecommendationUnavailable("failed")

        self.assertEqual(len(PlayMcpTavilyJobSearch(saramin, SimpleNamespace(search=unavailable)).search([])), 1)
        self.assertEqual(len(PlayMcpTavilyJobSearch(SimpleNamespace(search=unavailable), jobkorea).search([])), 1)
        with self.assertRaises(SaraminRecommendationUnavailable):
            PlayMcpTavilyJobSearch(SimpleNamespace(search=unavailable), SimpleNamespace(search=unavailable)).search([])

    def test_recommendation_includes_verified_postings_from_both_sources(self):
        saramin = SimpleNamespace(
            search=lambda _: [{"url": SARAMIN.format(number), "content": ""} for number in (1, 2, 4)],
            search_more=lambda _: [],
        )
        jobkorea = SimpleNamespace(search=lambda _: [{"url": JOBKOREA.format(3), "content": ""}])

        def verify(url, *, today):
            if "jobkorea" in url:
                time.sleep(0.02)
            number = url.rsplit("/", 1)[-1] if "jobkorea" in url else url.rsplit("=", 1)[-1]
            return ("회사" + number, "신입 백엔드 개발자", url, today.date(), "신입", "REST API 서버 개발")

        service = SaraminRecommendationService(
            PlayMcpTavilyJobSearch(saramin, jobkorea), SimpleNamespace(verify=verify),
        )
        result = service.recommend(SaraminRecommendationRequest(selected_ncs_ids=["skill-server"]))
        self.assertEqual(len(result.recommendations), 4)
        self.assertEqual({"saramin", "jobkorea"}, {
            "jobkorea" if "jobkorea" in item.source_url else "saramin"
            for item in result.recommendations
        })

    def test_new_provider_requires_tavily_key(self):
        with patch.dict(os.environ, {"JOB_SEARCH_PROVIDER": "playmcp_tavily", "TAVILY_API_KEY": ""}):
            with self.assertRaisesRegex(ValueError, "TAVILY_API_KEY"):
                build_saramin_recommendation_service_from_env()
        with patch.dict(os.environ, {"JOB_SEARCH_PROVIDER": "playmcp_tavily", "TAVILY_API_KEY": "test-key"}):
            service = build_saramin_recommendation_service_from_env()
            self.assertIsInstance(service.search, PlayMcpTavilyJobSearch)
            self.assertEqual(service.verifier.http.timeout.read, 3.0)

    def test_supplement_queries_are_distinct_private_and_deduplicated(self):
        requests = []
        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"results": [
                {"url": JOBKOREA.format(9)}, {"url": JOBKOREA.format(9)},
            ]})
        http = httpx.Client(transport=httpx.MockTransport(respond))
        result = TavilyJobKoreaSearch("test", http).search_more(["private README"])
        self.assertEqual(result, [{"url": JOBKOREA.format(9), "content": ""}])
        self.assertEqual(len({body["query"] for body in requests}), 2)
        self.assertTrue(all("/Recruit/GI_Read/" in body["query"] for body in requests))
        self.assertNotIn("private README", str(requests))

    def test_supplement_keeps_success_when_one_query_fails(self):
        def respond(request):
            query = json.loads(request.content)["query"]
            if "Java" in query:
                return httpx.Response(503)
            return httpx.Response(200, json={"results": [{"url": JOBKOREA.format(7)}]})
        http = httpx.Client(transport=httpx.MockTransport(respond))
        self.assertEqual(TavilyJobKoreaSearch("test", http).search_more([]),
                         [{"url": JOBKOREA.format(7), "content": ""}])

    def test_saramin_supplement_failure_does_not_discard_jobkorea(self):
        def unavailable(_):
            raise SaraminRecommendationUnavailable("unavailable")
        search = PlayMcpTavilyJobSearch(SimpleNamespace(search_more=unavailable),
                                      SimpleNamespace(search_more=lambda _: [{"url": JOBKOREA.format(3), "content": ""}]))
        self.assertEqual(search.search_more([]), [{"url": JOBKOREA.format(3), "content": ""}])

    def test_supplement_expands_one_jobkorea_to_five_verified_not_invalid_candidates(self):
        saramin = SimpleNamespace(search=lambda _: [], search_more=lambda _: [])
        jobkorea = SimpleNamespace(
            search=lambda _: [{"url": JOBKOREA.format(1), "content": ""}],
            search_more=lambda _: [{"url": JOBKOREA.format(i), "content": ""} for i in range(1, 9)],
        )
        checked = []
        def verify(url, *, today):
            number = url.rsplit("/", 1)[-1]
            checked.append(number)
            if number == "2":
                return None
            return ("회사" + number, "신입 백엔드 개발자", url, today.date(), "신입", "REST API 서버 개발")
        service = SaraminRecommendationService(PlayMcpTavilyJobSearch(saramin, jobkorea), SimpleNamespace(verify=verify))
        result = service.recommend(SaraminRecommendationRequest(selected_ncs_ids=["skill-server"]))
        self.assertEqual(len(result.recommendations), 5)
        self.assertEqual(checked.count("1"), 1)
        self.assertNotIn(JOBKOREA.format(2), [row.source_url for row in result.recommendations])


if __name__ == "__main__":
    unittest.main()
