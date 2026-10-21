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
from app.schemas.mofe_recruitment import MofeRecruitmentSearchResponse
from app.services.mofe_recruitment import (
    DEFAULT_MOFE_RECRUITMENT_API_URL,
    OFFICIAL_MOFE_DATASET_URL,
    MofeRecruitmentService,
    MofeRecruitmentSettings,
)


SAMPLE_ITEM = {
    "recrutPblntSn": 305259,
    "instNm": "한국전력공사",
    "recrutPbancTtl": "전문인력 백엔드 개발 채용공고",
    "pbancBgngYmd": "20260922",
    "pbancEndYmd": "20261006",
    "workRgnNmLst": "세종,충북",
    "hireTypeNmLst": "정규직",
    "recrutSeNm": "경력",
    "srcUrl": "http://recruit.example.org",
    "ncsCdNmLst": "정보통신",
    "aplyQlfcCn": "백엔드 API 개발 경력 2년 이상인 자",
    "prefCn": "클라우드 운영 경험 우대",
    "prefCondCn": "관련 자격증 보유자",
    "disqlfcRsn": "채용 결격사유가 있는 자",
    "scrnprcdrMthdExpln": "서류심사 후 면접",
}


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class FakeMofeHttpClient:
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


class FakeMofeRecruitmentService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return MofeRecruitmentSearchResponse(
            query=str(kwargs["query"]),
            page=int(kwargs["page"]),
            page_size=int(kwargs["page_size"]),
            total_count=1,
            recruitments=[{
                "announcement_id": 305259,
                "company": "한국전력공사",
                "title": "전문인력 백엔드 개발 채용공고",
                "source_url": None,
                "announced_at": "2026-09-22",
                "deadline": "2026-10-06",
                "location": "세종,충북",
                "employment_type": "정규직",
                "recruitment_type": "경력",
            }],
        )


class MofeRecruitmentServiceTest(unittest.TestCase):
    def test_filters_latest_ongoing_records_without_double_encoding_key(self):
        http = FakeMofeHttpClient([
            FakeResponse(200, {"resultCode": 200, "result": [SAMPLE_ITEM]}),
        ])
        service = MofeRecruitmentService(
            MofeRecruitmentSettings(
                "issued%2Bserver%2Bkey", DEFAULT_MOFE_RECRUITMENT_API_URL
            ),
            http,
        )

        result = service.search(query="백엔드")

        self.assertEqual(result.total_count, 1)
        self.assertEqual(result.recruitments[0].announcement_id, 305259)
        self.assertEqual(result.recruitments[0].deadline.isoformat(), "2026-10-06")
        self.assertIsNone(result.recruitments[0].source_url)
        request_url = str(http.requests[0]["url"])
        self.assertIn("serviceKey=issued%2Bserver%2Bkey", request_url)
        self.assertNotIn("issued%252Bserver%252Bkey", request_url)
        self.assertIn("ongoingYn=Y", request_url)

    def test_reloads_current_official_list_for_analysis_and_uses_safe_dataset_link(self):
        http = FakeMofeHttpClient([
            FakeResponse(200, {"resultCode": 200, "result": [SAMPLE_ITEM]}),
        ])
        service = MofeRecruitmentService(
            MofeRecruitmentSettings("test-key", DEFAULT_MOFE_RECRUITMENT_API_URL),
            http,
        )

        source_text, source_url = service.get_analysis_source(announcement_id=305259)

        self.assertIn("백엔드 API 개발 경력", source_text)
        self.assertIn("전형절차", source_text)
        self.assertEqual(source_url, OFFICIAL_MOFE_DATASET_URL)
        request_url = str(http.requests[0]["url"])
        self.assertIn("numOfRows=100", request_url)
        self.assertIn("ongoingYn=Y", request_url)
        self.assertNotIn("recrutPblntSn=", request_url)


class MofeRecruitmentApiTest(unittest.TestCase):
    def setUp(self):
        self.service = FakeMofeRecruitmentService()
        self.client = TestClient(create_app(
            token_verifier=FakeVerifier(),
            mofe_recruitment_service=self.service,
        ))

    def test_requires_login(self):
        response = self.client.get("/api/mofe/recruitments?query=%EB%B0%B1%EC%97%94%EB%93%9C")

        self.assertEqual(response.status_code, 401)

    def test_searches_authenticated_user_without_returning_key(self):
        response = self.client.get(
            "/api/mofe/recruitments?query=%EB%B0%B1%EC%97%94%EB%93%9C",
            headers={"Authorization": "Bearer owner-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recruitments"][0]["company"], "한국전력공사")
        self.assertEqual(self.service.calls, [{
            "query": "백엔드",
            "page": 1,
            "page_size": 10,
        }])
        self.assertNotIn("key", str(response.json()).lower())


if __name__ == "__main__":
    unittest.main()
