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
from app.schemas.incheon_recruitment import IncheonRecruitmentSearchResponse
from app.services.incheon_recruitment import (
    INCHEON_RECRUITMENT_API_URL,
    IncheonRecruitmentService,
    IncheonRecruitmentSettings,
    IncheonRecruitmentUnavailable,
)


def item(number: int, title: str, deadline: str = "2099-10-06 18:00", url: str | None = None):
    return {
        "rcrut_info_sn": number,
        "corp_nm": "인천 예시 회사",
        "rcrut_ttl": title,
        "url": url or f"https://www.incheon.go.kr/jobs/main/recruit/private/view.do?rcrutInfoSn={number}",
        "pbanc_bgng_dt": "2026-09-22 09:00",
        "pbanc_end_dt": deadline,
        "powk_addr": "인천 연수구",
        "work_type_nm": "정규직",
        "crr_se_nm": "경력",
    }


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, pages):
        self.pages = pages
        self.requests = []

    def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        page = kwargs["params"]["page"]
        return FakeResponse(self.pages[page])


class FakeVerifier:
    def verify_access_token(self, token):
        if token != "owner-token":
            raise InvalidAccessToken()
        return "owner"


class FakeService:
    def search(self, **kwargs):
        return IncheonRecruitmentSearchResponse(
            query=kwargs["query"],
            page=kwargs["page"],
            page_size=kwargs["page_size"],
            total_count=1,
            recruitments=[{
                "announcement_id": 1,
                "company": "인천 예시 회사",
                "title": "백엔드 개발자",
                "source_url": "https://www.incheon.go.kr/jobs/main/recruit/private/view.do?rcrutInfoSn=1",
            }],
        )


class IncheonRecruitmentServiceTest(unittest.TestCase):
    def test_searches_all_pages_and_excludes_expired_or_unsafe_rows(self):
        pages = {
            1: {"status": "OK", "data": {"count": 12, "list": [
                item(1, "디자이너"),
                item(2, "백엔드 개발자", "2020-01-01 18:00"),
                item(3, "백엔드 개발자", url="https://evil.example/jobs/main/recruit/private/view.do"),
                {**item(5, "백엔드 개발자"), "pbanc_bgng_dt": "2099-01-01 09:00"},
            ]}},
            2: {"status": "OK", "data": {"count": 12, "list": [item(4, "백엔드 개발자")]}}
        }
        http = FakeHttpClient(pages)
        service = IncheonRecruitmentService(IncheonRecruitmentSettings("secret-key"), http)

        result = service.search(query="백엔드")

        self.assertEqual(result.total_count, 1)
        self.assertEqual(result.recruitments[0].announcement_id, 4)
        self.assertEqual(len(http.requests), 2)
        self.assertEqual(http.requests[0][0], INCHEON_RECRUITMENT_API_URL)
        self.assertEqual(http.requests[0][1]["params"], {"key": "secret-key", "page": 1})
        self.assertNotIn("secret-key", result.model_dump_json())

    def test_rejects_provider_failure_without_leaking_key(self):
        http = FakeHttpClient({1: {"status": "FAIL", "code": "010"}})
        service = IncheonRecruitmentService(IncheonRecruitmentSettings("secret-key"), http)

        with self.assertRaises(IncheonRecruitmentUnavailable) as context:
            service.search(query="개발")

        self.assertNotIn("secret-key", str(context.exception))


class IncheonRecruitmentApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(
            token_verifier=FakeVerifier(),
            incheon_recruitment_service=FakeService(),
        ))

    def test_requires_login(self):
        response = self.client.get("/api/incheon/recruitments?query=개발")
        self.assertEqual(response.status_code, 401)

    def test_returns_provider_results_for_authenticated_user(self):
        response = self.client.get(
            "/api/incheon/recruitments?query=백엔드",
            headers={"Authorization": "Bearer owner-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recruitments"][0]["title"], "백엔드 개발자")
        self.assertNotIn("key", str(response.json()).lower())


if __name__ == "__main__":
    unittest.main()
