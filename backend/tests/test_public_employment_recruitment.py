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
from app.schemas.public_employment_recruitment import (
    PublicEmploymentRecruitmentSearchResponse,
)
from app.services.public_employment_recruitment import (
    DEFAULT_PUBLIC_EMPLOYMENT_API_URL,
    PublicEmploymentRecruitmentService,
    PublicEmploymentRecruitmentSettings,
)


LIST_XML = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<response><header><resultCode>00</resultCode></header><body><totalCount>1</totalCount><items><item>
<idx>456</idx><insttname>인사혁신처 예시 기관</insttname><title>계약직 개발자 공고</title>
<regdate>20260922</regdate><enddate>20261006</enddate><areanm>서울</areanm>
<type01>계약직</type01><type02>경력경쟁채용</type02>
</item></items></body></response>"""

DETAIL_XML = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<response><header><resultCode>00</resultCode></header><body><items><item>
<idx>456</idx><contents><![CDATA[업무내용: API 오류 원인을 분석하고 개선한 경험이 있는 개발자를 모집합니다.]]></contents>
<link01>www.recruit.example.org/jobs/456</link01>
</item></items></body></response>"""


class FakeResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content


class FakePublicEmploymentHttpClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def get(self, url: str, **kwargs):
        self.requests.append({"url": url, **kwargs})
        return self.responses.pop(0)


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        if token != "owner-token":
            raise InvalidAccessToken()
        return "owner"


class FakePublicEmploymentRecruitmentService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return PublicEmploymentRecruitmentSearchResponse(
            query=str(kwargs["query"]),
            page=int(kwargs["page"]),
            page_size=int(kwargs["page_size"]),
            total_count=1,
            recruitments=[{
                "announcement_id": 456,
                "company": "인사혁신처 예시 기관",
                "title": "계약직 개발자 공고",
                "announced_at": "2026-09-22",
                "deadline": "2026-10-06",
                "location": "서울",
                "employment_type": "계약직",
                "recruitment_type": "경력경쟁채용",
            }],
        )


class PublicEmploymentRecruitmentServiceTest(unittest.TestCase):
    def test_uses_configured_key_without_double_encoding_and_normalizes_list(self):
        http = FakePublicEmploymentHttpClient([
            FakeResponse(200, LIST_XML.encode()),
        ])
        service = PublicEmploymentRecruitmentService(
            PublicEmploymentRecruitmentSettings(
                api_key="issued%2Bserver%2Bkey",
                api_url=DEFAULT_PUBLIC_EMPLOYMENT_API_URL,
            ),
            http,
        )

        result = service.search(query=" 개발 ")

        self.assertEqual(result.query, "개발")
        self.assertEqual(result.recruitments[0].deadline.isoformat(), "2026-10-06")
        request_url = str(http.requests[0]["url"])
        self.assertIn("serviceKey=issued%2Bserver%2Bkey", request_url)
        self.assertNotIn("issued%252Bserver%252Bkey", request_url)
        self.assertIn("Kwrd=%EA%B0%9C%EB%B0%9C", request_url)

    def test_uses_detail_source_text_and_https_original_link_for_analysis(self):
        http = FakePublicEmploymentHttpClient([
            FakeResponse(200, DETAIL_XML.encode()),
        ])
        service = PublicEmploymentRecruitmentService(
            PublicEmploymentRecruitmentSettings("test-key", DEFAULT_PUBLIC_EMPLOYMENT_API_URL),
            http,
        )

        source_text, source_url = service.get_analysis_source(announcement_id=456)

        self.assertIn("API 오류 원인을 분석", source_text)
        self.assertEqual(source_url, "https://www.recruit.example.org/jobs/456")
        self.assertIn("idx=456", str(http.requests[0]["url"]))


class PublicEmploymentRecruitmentApiTest(unittest.TestCase):
    def setUp(self):
        self.service = FakePublicEmploymentRecruitmentService()
        self.client = TestClient(create_app(
            token_verifier=FakeVerifier(),
            public_employment_recruitment_service=self.service,
        ))

    def test_requires_login(self):
        response = self.client.get("/api/public-employment/recruitments?query=%EA%B0%9C%EB%B0%9C")

        self.assertEqual(response.status_code, 401)

    def test_searches_for_authenticated_user_without_returning_key(self):
        response = self.client.get(
            "/api/public-employment/recruitments?query=%EA%B0%9C%EB%B0%9C",
            headers={"Authorization": "Bearer owner-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recruitments"][0]["title"], "계약직 개발자 공고")
        self.assertEqual(self.service.calls, [{
            "query": "개발",
            "page": 1,
            "page_size": 10,
        }])
        self.assertNotIn("key", str(response.json()).lower())


if __name__ == "__main__":
    unittest.main()
