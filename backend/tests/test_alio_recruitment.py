from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import InvalidAccessToken
from app.main import create_app
from app.schemas.alio_recruitment import AlioRecruitmentSearchResponse
from app.services.alio_recruitment import (
    DEFAULT_ALIO_RECRUITMENT_API_URL,
    AlioRecruitmentService,
    AlioRecruitmentSettings,
)


class FakeResponse:
    def __init__(self, status_code: int, body: object) -> None:
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


class FakeAlioHttpClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.request: dict[str, object] | None = None

    def post(self, url: str, **kwargs):
        self.request = {"url": url, **kwargs}
        return self.response


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        if token != "owner-token":
            raise InvalidAccessToken()
        return "owner"


class FakeAlioRecruitmentService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.analysis_source_calls: list[dict[str, object]] = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return AlioRecruitmentSearchResponse(
            query=str(kwargs["query"]),
            page=int(kwargs["page"]),
            page_size=int(kwargs["page_size"]),
            total_count=1,
            recruitments=[{
                "announcement_id": 123,
                "company": "한국 예시 공사",
                "title": "신입 백엔드 개발자",
                "source_url": "https://example.invalid/job",
                "announced_at": "2026-09-21",
                "deadline": "2026-10-06",
                "location": "서울",
                "employment_type": "정규직",
                "recruitment_type": "신입",
            }],
        )

    def get_analysis_source(self, **kwargs):
        self.analysis_source_calls.append(kwargs)
        return "지원자격: API 오류 원인 분석 및 개선 경험 보유자"


class AlioRecruitmentServiceTest(unittest.TestCase):
    def test_posts_server_key_and_normalizes_alio_result(self):
        http = FakeAlioHttpClient(FakeResponse(200, {
            "data": {
                "resultCode": 200,
                "totalCount": 1,
                "result": [{
                    "recrutPblntSn": 123,
                    "instNm": "한국 예시 공사",
                    "recrutPbancTtl": "신입 백엔드 개발자",
                    "srcUrl": "https://example.invalid/job",
                    "pbancBgngYmd": "20260921",
                    "pbancEndYmd": "20261006",
                    "workRgnNmLst": "서울",
                    "hireTypeNmLst": "정규직",
                    "recrutSeNm": "신입",
                }],
            },
        }))
        service = AlioRecruitmentService(
            AlioRecruitmentSettings(
                api_key="test-server-only-key",
                api_url=DEFAULT_ALIO_RECRUITMENT_API_URL,
                api_key_param="authKey",
            ),
            http,
        )

        result = service.search(query=" 백엔드 ")

        self.assertEqual(result.query, "백엔드")
        self.assertEqual(result.recruitments[0].deadline.isoformat(), "2026-10-06")
        self.assertEqual(http.request["url"], DEFAULT_ALIO_RECRUITMENT_API_URL)
        self.assertEqual(http.request["data"]["authKey"], "test-server-only-key")
        self.assertEqual(http.request["data"]["ongoingYn"], "Y")
        self.assertEqual(http.request["data"]["recrutPbancTtl"], "백엔드")

    def test_removes_unsafe_source_url_from_result(self):
        http = FakeAlioHttpClient(FakeResponse(200, {
            "data": {
                "resultCode": 200,
                "totalCount": 1,
                "result": [{
                    "recrutPblntSn": 123,
                    "instNm": "한국 예시 공사",
                    "recrutPbancTtl": "신입 백엔드 개발자",
                    "srcUrl": "javascript:alert(1)",
                }],
            },
        }))
        service = AlioRecruitmentService(
            AlioRecruitmentSettings(
                api_key="test-server-only-key",
                api_url=DEFAULT_ALIO_RECRUITMENT_API_URL,
                api_key_param="authKey",
            ),
            http,
        )

        result = service.search(query="백엔드")

        self.assertIsNone(result.recruitments[0].source_url)

    def test_reloads_official_requirement_fields_for_analysis(self):
        http = FakeAlioHttpClient(FakeResponse(200, {
            "data": {
                "resultCode": 200,
                "totalCount": 1,
                "result": [{
                    "recrutPblntSn": 123,
                    "recrutPbancTtl": "신입 백엔드 개발자",
                    "aplyQlfcCn": "<p>Java 기반 API 개발 경험 보유자</p>",
                    "prefCn": "SQL 활용 경험 우대",
                    "acbgCondNmLst": "학사 이상",
                }],
            },
        }))
        service = AlioRecruitmentService(
            AlioRecruitmentSettings(
                api_key="test-server-only-key",
                api_url=DEFAULT_ALIO_RECRUITMENT_API_URL,
                api_key_param="authKey",
            ),
            http,
        )

        source_text = service.get_analysis_source(
            announcement_id=123,
            title="신입 백엔드 개발자",
        )

        self.assertEqual(
            source_text,
            "지원자격: Java 기반 API 개발 경험 보유자\n우대사항: SQL 활용 경험 우대\n학력요건: 학사 이상",
        )
        self.assertEqual(http.request["data"]["recrutPbancTtl"], "신입 백엔드 개발자")


class AlioRecruitmentApiTest(unittest.TestCase):
    def setUp(self):
        self.service = FakeAlioRecruitmentService()
        self.client = TestClient(create_app(
            token_verifier=FakeVerifier(),
            alio_recruitment_service=self.service,
        ))

    def test_requires_login(self):
        response = self.client.get("/api/alio/recruitments?query=%EB%B0%B1%EC%97%94%EB%93%9C")

        self.assertEqual(response.status_code, 401)

    def test_searches_for_authenticated_user_without_returning_key(self):
        response = self.client.get(
            "/api/alio/recruitments?query=%EB%B0%B1%EC%97%94%EB%93%9C",
            headers={"Authorization": "Bearer owner-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recruitments"][0]["title"], "신입 백엔드 개발자")
        self.assertEqual(self.service.calls, [{
            "query": "백엔드",
            "page": 1,
            "page_size": 10,
        }])
        self.assertNotIn("key", str(response.json()).lower())

    def test_rejects_empty_or_too_long_query_without_calling_alio(self):
        empty = self.client.get(
            "/api/alio/recruitments?query=%20%20",
            headers={"Authorization": "Bearer owner-token"},
        )
        too_long = self.client.get(
            f"/api/alio/recruitments?query={'a' * 81}",
            headers={"Authorization": "Bearer owner-token"},
        )

        self.assertEqual(empty.status_code, 422)
        self.assertEqual(too_long.status_code, 422)
        self.assertEqual(self.service.calls, [])


if __name__ == "__main__":
    unittest.main()
