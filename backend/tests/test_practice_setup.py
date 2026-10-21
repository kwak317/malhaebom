from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import InvalidAccessToken
from app.core.supabase_settings import SupabaseSettings
from app.main import create_app
from app.schemas.alio_recruitment import (
    AlioRecruitmentAnalysisRequest,
    SaveAnalyzedAlioRecruitmentRequest,
)
from app.schemas.public_employment_recruitment import (
    SaveAnalyzedPublicEmploymentRecruitmentRequest,
)
from app.schemas.mofe_recruitment import SaveAnalyzedMofeRecruitmentRequest
from app.schemas.saramin_recommendation import SaveReviewedPrivateJobRequest
from app.schemas.practice_setup import CreatePracticeSessionRequest
from app.services.practice_setup import PracticeSetupService
from app.services.supabase_practice_setup import SupabasePracticeSetupRepository


JOB_ID = "10000000-0000-4000-8000-000000000001"
REQ_ONE = "20000000-0000-4000-8000-000000000001"
REQ_TWO = "20000000-0000-4000-8000-000000000002"
SESSION_ID = "30000000-0000-4000-8000-000000000001"
ALIO_JOB_ID = "10000000-0000-4000-8000-000000000009"
ALIO_REQ_ID = "20000000-0000-4000-8000-000000000009"
PUBLIC_JOB_ID = "10000000-0000-4000-8000-000000000010"
PUBLIC_REQ_ID = "20000000-0000-4000-8000-000000000010"
MOFE_JOB_ID = "10000000-0000-4000-8000-000000000011"
MOFE_REQ_ID = "20000000-0000-4000-8000-000000000011"


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        if token != "owner-token":
            raise InvalidAccessToken()
        return "owner"


class FakePracticeSetupRepository:
    def __init__(self) -> None:
        self.created_request: CreatePracticeSessionRequest | None = None
        self.analyzed_request: SaveAnalyzedAlioRecruitmentRequest | None = None
        self.public_analyzed_request: SaveAnalyzedPublicEmploymentRecruitmentRequest | None = None
        self.mofe_analyzed_request: SaveAnalyzedMofeRecruitmentRequest | None = None

    def list_job_postings(self, user):
        postings = [{
            "id": JOB_ID,
            "company": "말해봄 평가용 가상 회사",
            "title": "연습용 신입 백엔드 개발자 공고 A",
            "source_url": "https://example.invalid/demo-job-01",
            "captured_at": "2026-09-17T00:00:00Z",
            "data_origin": "demo",
            "job_requirements": [
                {"id": REQ_TWO, "code": "J01-R2", "requirement_text": "회귀 확인", "source_excerpt": None, "display_order": 2},
                {"id": REQ_ONE, "code": "J01-R1", "requirement_text": "오류 분석", "source_excerpt": None, "display_order": 1},
            ],
        }]
        if self.analyzed_request is not None:
            postings.append({
                "id": ALIO_JOB_ID,
                "company": self.analyzed_request.company,
                "title": self.analyzed_request.title,
                "source_url": self.analyzed_request.source_url,
                "captured_at": "2026-09-21T00:00:00Z",
                "data_origin": "alio",
                "job_requirements": [{
                    "id": ALIO_REQ_ID,
                    "code": "ALIO-123-R1",
                    "requirement_text": self.analyzed_request.requirements[0].text,
                    "source_excerpt": self.analyzed_request.requirements[0].source_excerpt,
                    "display_order": 1,
                }],
            })
        if self.public_analyzed_request is not None:
            postings.append({
                "id": PUBLIC_JOB_ID,
                "company": self.public_analyzed_request.company,
                "title": self.public_analyzed_request.title,
                "source_url": self.public_analyzed_request.source_url,
                "captured_at": "2026-09-22T00:00:00Z",
                "data_origin": "public_job",
                "job_requirements": [{
                    "id": PUBLIC_REQ_ID,
                    "code": "MPO-456-R1",
                    "requirement_text": self.public_analyzed_request.requirements[0].text,
                    "source_excerpt": self.public_analyzed_request.requirements[0].source_excerpt,
                    "display_order": 1,
                }],
            })
        if self.mofe_analyzed_request is not None:
            postings.append({
                "id": MOFE_JOB_ID,
                "company": self.mofe_analyzed_request.company,
                "title": self.mofe_analyzed_request.title,
                "source_url": self.mofe_analyzed_request.source_url,
                "captured_at": "2026-09-22T00:00:00Z",
                "data_origin": "mofe_job",
                "job_requirements": [{
                    "id": MOFE_REQ_ID,
                    "code": "MOFE-305259-R1",
                    "requirement_text": self.mofe_analyzed_request.requirements[0].text,
                    "source_excerpt": self.mofe_analyzed_request.requirements[0].source_excerpt,
                    "display_order": 1,
                }],
            })
        return postings

    def create_practice_session(self, user, request):
        self.created_request = request
        return SESSION_ID

    def save_analyzed_alio_recruitment(self, user, request):
        self.analyzed_request = request
        return ALIO_JOB_ID

    def save_analyzed_public_employment_recruitment(self, user, request):
        self.public_analyzed_request = request
        return PUBLIC_JOB_ID

    def save_analyzed_mofe_recruitment(self, user, request):
        self.mofe_analyzed_request = request
        return MOFE_JOB_ID

    def get_practice_session(self, user, practice_session_id):
        if practice_session_id != SESSION_ID:
            raise KeyError(practice_session_id)
        return {"expires_at": "2026-09-18T00:00:00Z"}


class FakeResponse:
    def __init__(self, status_code: int, body: object) -> None:
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


class FakeHttpClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


class FakeAlioRequirementAnalysisService:
    def __init__(self) -> None:
        self.request: AlioRecruitmentAnalysisRequest | None = None
        self.source_text: str | None = None

    def analyze(self, request: AlioRecruitmentAnalysisRequest, *, source_text: str | None = None):
        self.request = request
        self.source_text = source_text
        return [{
            "text": "API 오류 분석 경험",
            "source_excerpt": "지원자격: API 오류 원인 분석 및 개선 경험 보유자",
        }]


class FakeAlioRecruitmentService:
    def __init__(self) -> None:
        self.analysis_source_calls: list[dict[str, object]] = []

    def get_analysis_source(self, **kwargs):
        self.analysis_source_calls.append(kwargs)
        return "지원자격: API 오류 원인 분석 및 개선 경험 보유자"


class FakePublicEmploymentRecruitmentService:
    def __init__(self) -> None:
        self.analysis_source_calls: list[dict[str, object]] = []

    def get_analysis_source(self, **kwargs):
        self.analysis_source_calls.append(kwargs)
        return (
            "업무내용: API 오류 원인을 분석하고 개선한 경험이 있는 개발자를 모집합니다.",
            "https://recruit.example.org/jobs/456",
        )


class FakeMofeRecruitmentService:
    def __init__(self) -> None:
        self.analysis_source_calls: list[dict[str, object]] = []

    def get_analysis_source(self, **kwargs):
        self.analysis_source_calls.append(kwargs)
        return (
            "지원자격: 백엔드 API 개발 경력 2년 이상인 자\n전형절차: 서류심사 후 면접",
            "https://www.data.go.kr/data/15125273/openapi.do",
        )


class PracticeSetupApiTest(unittest.TestCase):
    def setUp(self):
        self.repository = FakePracticeSetupRepository()
        self.analysis_service = FakeAlioRequirementAnalysisService()
        self.alio_service = FakeAlioRecruitmentService()
        self.public_employment_service = FakePublicEmploymentRecruitmentService()
        self.mofe_service = FakeMofeRecruitmentService()
        self.client = TestClient(create_app(
            token_verifier=FakeVerifier(),
            practice_setup_service=PracticeSetupService(self.repository),
            alio_recruitment_service=self.alio_service,
            public_employment_recruitment_service=self.public_employment_service,
            mofe_recruitment_service=self.mofe_service,
            alio_requirement_analysis_service=self.analysis_service,
        ))

    def test_requires_login_to_read_job_postings(self):
        response = self.client.get("/api/job-postings")
        self.assertEqual(response.status_code, 401)

    def test_lists_reviewed_job_with_ordered_requirements(self):
        response = self.client.get(
            "/api/job-postings",
            headers={"Authorization": "Bearer owner-token"},
        )
        self.assertEqual(response.status_code, 200)
        posting = response.json()["job_postings"][0]
        self.assertEqual(posting["data_origin"], "demo")
        self.assertEqual(
            [item["code"] for item in posting["requirements"]],
            ["J01-R1", "J01-R2"],
        )

    def test_creates_practice_session_with_one_or_two_requirements(self):
        response = self.client.post(
            "/api/practice-sessions",
            headers={"Authorization": "Bearer owner-token"},
            json={
                "job_posting_id": JOB_ID,
                "requirement_ids": [REQ_ONE, REQ_TWO],
                "question_type": "preset",
                "question_id": "preset-04",
                "custom_question_text": None,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["practice_session_id"], SESSION_ID)
        self.assertEqual(len(self.repository.created_request.requirement_ids), 2)

    def test_rejects_duplicate_or_more_than_two_requirements(self):
        for requirement_ids in ([REQ_ONE, REQ_ONE], [REQ_ONE, REQ_TWO, SESSION_ID]):
            response = self.client.post(
                "/api/practice-sessions",
                headers={"Authorization": "Bearer owner-token"},
                json={
                    "job_posting_id": JOB_ID,
                    "requirement_ids": requirement_ids,
                    "question_type": "preset",
                    "question_id": "preset-04",
                    "custom_question_text": None,
                },
            )
            self.assertEqual(response.status_code, 422)

    def test_analyzes_alio_source_and_saves_requirements_for_coaching(self):
        response = self.client.post(
            "/api/alio/recruitments/analyze",
            headers={"Authorization": "Bearer owner-token"},
            json={
                "announcement_id": 123,
                "company": "한국 예시 공사",
                "title": "신입 백엔드 개발자",
                "source_url": "https://recruit.example.org/jobs/123",
            },
        )
        self.assertEqual(response.status_code, 201)
        posting = response.json()
        self.assertEqual(posting["id"], ALIO_JOB_ID)
        self.assertEqual(posting["data_origin"], "alio")
        self.assertEqual(
            posting["requirements"][0]["source_excerpt"],
            "지원자격: API 오류 원인 분석 및 개선 경험 보유자",
        )
        self.assertEqual(self.analysis_service.request.announcement_id, 123)
        self.assertEqual(
            self.analysis_service.source_text,
            "지원자격: API 오류 원인 분석 및 개선 경험 보유자",
        )
        self.assertEqual(self.alio_service.analysis_source_calls, [{
            "announcement_id": 123,
            "title": "신입 백엔드 개발자",
        }])
        self.assertEqual(self.repository.analyzed_request.requirements[0].text, "API 오류 분석 경험")

    def test_rejects_non_https_source_when_analyzing(self):
        response = self.client.post(
            "/api/alio/recruitments/analyze",
            headers={"Authorization": "Bearer owner-token"},
            json={
                "announcement_id": 123,
                "company": "한국 예시 공사",
                "title": "신입 백엔드 개발자",
                "source_url": "ftp://example.invalid/recruitment/123",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_analyzes_public_employment_source_and_saves_requirements_for_coaching(self):
        response = self.client.post(
            "/api/public-employment/recruitments/analyze",
            headers={"Authorization": "Bearer owner-token"},
            json={
                "announcement_id": 456,
                "company": "인사혁신처 예시 기관",
                "title": "계약직 개발자 공고",
            },
        )

        self.assertEqual(response.status_code, 201)
        posting = response.json()
        self.assertEqual(posting["id"], PUBLIC_JOB_ID)
        self.assertEqual(posting["data_origin"], "public_job")
        self.assertEqual(
            self.public_employment_service.analysis_source_calls,
            [{"announcement_id": 456}],
        )
        self.assertEqual(
            self.analysis_service.source_text,
            "업무내용: API 오류 원인을 분석하고 개선한 경험이 있는 개발자를 모집합니다.",
        )
        self.assertEqual(
            self.repository.public_analyzed_request.source_url,
            "https://recruit.example.org/jobs/456",
        )

    def test_analyzes_mofe_source_and_saves_requirements_for_coaching(self):
        response = self.client.post(
            "/api/mofe/recruitments/analyze",
            headers={"Authorization": "Bearer owner-token"},
            json={
                "announcement_id": 305259,
                "company": "한국전력공사",
                "title": "전문인력 백엔드 개발 채용공고",
            },
        )

        self.assertEqual(response.status_code, 201)
        posting = response.json()
        self.assertEqual(posting["id"], MOFE_JOB_ID)
        self.assertEqual(posting["data_origin"], "mofe_job")
        self.assertEqual(
            self.mofe_service.analysis_source_calls,
            [{"announcement_id": 305259}],
        )
        self.assertIn("백엔드 API 개발", self.analysis_service.source_text)
        self.assertEqual(
            self.repository.mofe_analyzed_request.source_url,
            "https://www.data.go.kr/data/15125273/openapi.do",
        )


class SupabasePracticeSetupRepositoryTest(unittest.TestCase):
    def test_uses_user_jwt_for_catalog_and_atomic_session_rpc(self):
        rows = [{
            "id": JOB_ID,
            "company": "가상 회사",
            "title": "백엔드",
            "source_url": "https://example.invalid/job",
            "captured_at": "2026-09-17T00:00:00Z",
            "data_origin": "demo",
            "job_requirements": [],
        }]
        http = FakeHttpClient([
            FakeResponse(200, rows),
            FakeResponse(200, SESSION_ID),
        ])
        repository = SupabasePracticeSetupRepository(
            SupabaseSettings("https://project.supabase.co", "publishable-key"),
            http,
        )
        user = type("User", (), {"user_id": "owner", "access_token": "user-token"})()

        self.assertEqual(repository.list_job_postings(user), rows)
        created = repository.create_practice_session(
            user,
            CreatePracticeSessionRequest(
                job_posting_id=JOB_ID,
                requirement_ids=[REQ_ONE],
                question_type="preset",
                question_id="preset-04",
            ),
        )

        self.assertEqual(created, SESSION_ID)
        self.assertTrue(http.requests[0]["url"].endswith("order=company.asc,title.asc"))
        self.assertTrue(http.requests[1]["url"].endswith("/rest/v1/rpc/create_practice_session"))
        self.assertTrue(all(
            request["headers"]["Authorization"] == "Bearer user-token"
            for request in http.requests
        ))

    def test_uses_user_jwt_to_save_ai_analyzed_alio_evidence(self):
        http = FakeHttpClient([FakeResponse(201, ALIO_JOB_ID)])
        repository = SupabasePracticeSetupRepository(
            SupabaseSettings("https://project.supabase.co", "publishable-key"),
            http,
        )
        user = type("User", (), {"user_id": "owner", "access_token": "user-token"})()

        created = repository.save_analyzed_alio_recruitment(
            user,
            SaveAnalyzedAlioRecruitmentRequest(
                announcement_id=123,
                company="한국 예시 공사",
                title="신입 백엔드 개발자",
                source_url="https://www.alio.go.kr/recruitment/123",
                requirements=[{
                    "text": "API 오류 분석 경험",
                    "source_excerpt": "지원자격: API 오류 원인 분석 및 개선 경험 보유자",
                }],
            ),
        )

        self.assertEqual(created, ALIO_JOB_ID)
        request = http.requests[0]
        self.assertTrue(request["url"].endswith("/rest/v1/rpc/review_alio_recruitment"))
        self.assertEqual(request["headers"]["Authorization"], "Bearer user-token")
        self.assertEqual(request["json"], {
            "p_announcement_id": 123,
            "p_company": "한국 예시 공사",
            "p_title": "신입 백엔드 개발자",
            "p_source_url": "https://www.alio.go.kr/recruitment/123",
            "p_requirements": [{
                "text": "API 오류 분석 경험",
                "source_excerpt": "지원자격: API 오류 원인 분석 및 개선 경험 보유자",
            }],
        })

    def test_uses_user_jwt_to_save_ai_analyzed_public_employment_evidence(self):
        http = FakeHttpClient([FakeResponse(201, PUBLIC_JOB_ID)])
        repository = SupabasePracticeSetupRepository(
            SupabaseSettings("https://project.supabase.co", "publishable-key"),
            http,
        )
        user = type("User", (), {"user_id": "owner", "access_token": "user-token"})()

        created = repository.save_analyzed_public_employment_recruitment(
            user,
            SaveAnalyzedPublicEmploymentRecruitmentRequest(
                announcement_id=456,
                company="인사혁신처 예시 기관",
                title="계약직 개발자 공고",
                source_url="https://recruit.example.org/jobs/456",
                requirements=[{
                    "text": "API 오류 분석 경험",
                    "source_excerpt": "업무내용: API 오류 원인을 분석하고 개선한 경험",
                }],
            ),
        )

        self.assertEqual(created, PUBLIC_JOB_ID)
        request = http.requests[0]
        self.assertTrue(request["url"].endswith("/rest/v1/rpc/review_public_employment_recruitment"))
        self.assertEqual(request["headers"]["Authorization"], "Bearer user-token")
        self.assertEqual(request["json"]["p_announcement_id"], 456)

    def test_uses_user_jwt_to_save_ai_analyzed_mofe_evidence(self):
        http = FakeHttpClient([FakeResponse(201, MOFE_JOB_ID)])
        repository = SupabasePracticeSetupRepository(
            SupabaseSettings("https://project.supabase.co", "publishable-key"),
            http,
        )
        user = type("User", (), {"user_id": "owner", "access_token": "user-token"})()

        created = repository.save_analyzed_mofe_recruitment(
            user,
            SaveAnalyzedMofeRecruitmentRequest(
                announcement_id=305259,
                company="한국전력공사",
                title="전문인력 백엔드 개발 채용공고",
                source_url="https://www.data.go.kr/data/15125273/openapi.do",
                requirements=[{
                    "text": "백엔드 API 개발 경험",
                    "source_excerpt": "지원자격: 백엔드 API 개발 경력 2년 이상인 자",
                }],
            ),
        )

        self.assertEqual(created, MOFE_JOB_ID)
        request = http.requests[0]
        self.assertTrue(request["url"].endswith("/rest/v1/rpc/review_mofe_recruitment"))
        self.assertEqual(request["headers"]["Authorization"], "Bearer user-token")
        self.assertEqual(request["json"]["p_announcement_id"], 305259)

    def test_private_job_review_rpc_uses_server_key_after_user_verification(self):
        http = FakeHttpClient([FakeResponse(200, "10000000-0000-4000-8000-000000000020")])
        repository = SupabasePracticeSetupRepository(
            SupabaseSettings("https://project.supabase.co", "publishable-key", "server-only-key"),
            http,
        )
        user = type("User", (), {
            "user_id": "50000000-0000-4000-8000-000000000003",
            "access_token": "user-token",
        })()
        saved = repository.save_reviewed_private_job(user, SaveReviewedPrivateJobRequest(
            source="saramin",
            posting_id="123",
            company="예시기업",
            title="신입 백엔드 개발자",
            source_url="https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=123",
            requirements=[{
                "text": "REST API 서버 개발",
                "source_excerpt": "REST API 서버 개발",
            }],
        ))
        self.assertEqual(saved, "10000000-0000-4000-8000-000000000020")
        request = http.requests[0]
        self.assertTrue(request["url"].endswith("/rest/v1/rpc/review_private_job_recruitment"))
        self.assertEqual(request["headers"]["Authorization"], "Bearer server-only-key")
        self.assertEqual(request["json"]["p_reviewer_id"], user.user_id)
        self.assertEqual(request["json"]["p_requirements"][0]["source_excerpt"], "REST API 서버 개발")

if __name__ == "__main__":
    unittest.main()
