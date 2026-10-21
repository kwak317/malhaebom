from __future__ import annotations

import sys
import unittest
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import AuthenticatedUser, InvalidAccessToken  # noqa: E402
from app.core.supabase_settings import SupabaseSettings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.schemas.answer_revision import AnswerRevisionCreateRequest  # noqa: E402
from app.services.answer_revisions import (  # noqa: E402
    AnswerRevisionService,
    normalize_confirmed_text,
    split_answer_segments,
)
from app.services.supabase_answer_revisions import (  # noqa: E402
    SupabaseAnswerRevisionRepository,
)


JOB_ID = UUID("30000000-0000-4000-8000-000000000001")
REVISION_ID = UUID("40000000-0000-4000-8000-000000000001")
SESSION_ID = UUID("50000000-0000-4000-8000-000000000001")
JOB_SNAPSHOT_ID = UUID("60000000-0000-4000-8000-000000000001")
USER = AuthenticatedUser("user-owner", "owner-token")


class FakeVerifier:
    def verify_access_token(self, token: str) -> str:
        if token != "owner-token":
            raise InvalidAccessToken()
        return "user-owner"


class FakeRepository:
    def __init__(self) -> None:
        self.text = ""
        self.segments = []

    def create_revision(self, user, *, analysis_job_id, confirmed_text, answer_segments):
        self.text = confirmed_text
        self.segments = answer_segments
        return {
            "id": str(REVISION_ID),
            "analysis_job_id": str(analysis_job_id),
            "practice_session_id": str(SESSION_ID),
            "question_id": "preset-04",
            "answer_segments": [item.model_dump(mode="json") for item in answer_segments],
            "confirmed_at": "2026-09-17T07:00:00Z",
            "expires_at": "2026-09-18T07:00:00Z",
        }

    def get_job_snapshot_id(self, user, practice_session_id):
        return JOB_SNAPSHOT_ID


class FakeResponse:
    def __init__(self, status_code: int, body: object) -> None:
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


class AnswerRevisionTest(unittest.TestCase):
    def setUp(self):
        self.repository = FakeRepository()
        self.service = AnswerRevisionService(self.repository)

    def test_normalizes_and_splits_confirmed_text_into_server_ids(self):
        normalized = normalize_confirmed_text(
            "  로그인 오류가 발생했습니다.   \n 로그를 확인해 수정했습니다.  "
        )
        segments = split_answer_segments(normalized)

        self.assertEqual(
            [item.text for item in segments],
            ["로그인 오류가 발생했습니다.", "로그를 확인해 수정했습니다."],
        )
        self.assertTrue(all(item.segment_id.startswith("segment-") for item in segments))

    def test_service_returns_immutable_revision_and_selected_job_id(self):
        result = self.service.confirm(
            USER,
            JOB_ID,
            AnswerRevisionCreateRequest(
                confirmed_text="오류를 재현했습니다. 로그를 확인했습니다."
            ),
        )

        self.assertEqual(result.answer_revision_id, REVISION_ID)
        self.assertEqual(result.job_snapshot_id, JOB_SNAPSHOT_ID)
        self.assertEqual(len(result.answer_segments), 2)
        self.assertEqual(self.repository.text, "오류를 재현했습니다. 로그를 확인했습니다.")

    def test_api_requires_login_and_creates_revision(self):
        client = TestClient(
            create_app(
                token_verifier=FakeVerifier(),
                answer_revision_service=self.service,
            )
        )
        path = f"/analysis-jobs/{JOB_ID}/answer-revisions"

        self.assertEqual(
            client.post(path, json={"confirmed_text": "확정 답변입니다."}).status_code,
            401,
        )
        response = client.post(
            path,
            headers={"Authorization": "Bearer owner-token"},
            json={"confirmed_text": "확정 답변입니다."},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["answer_revision_id"], str(REVISION_ID))

    def test_supabase_repository_uses_user_jwt_and_rpc(self):
        row = {
            "id": str(REVISION_ID),
            "analysis_job_id": str(JOB_ID),
            "practice_session_id": str(SESSION_ID),
            "question_id": "preset-04",
            "answer_segments": [{"segment_id": "s1", "text": "확정 답변"}],
            "confirmed_at": "2026-09-17T07:00:00Z",
            "expires_at": "2026-09-18T07:00:00Z",
        }
        http = FakeHttp(
            [
                FakeResponse(200, str(REVISION_ID)),
                FakeResponse(200, [row]),
                FakeResponse(200, [{"job_posting_id": str(JOB_SNAPSHOT_ID)}]),
            ]
        )
        repository = SupabaseAnswerRevisionRepository(
            SupabaseSettings("https://project.supabase.co", "publishable"), http
        )
        segment = split_answer_segments("확정 답변")

        created = repository.create_revision(
            USER,
            analysis_job_id=JOB_ID,
            confirmed_text="확정 답변",
            answer_segments=segment,
        )
        snapshot_id = repository.get_job_snapshot_id(USER, SESSION_ID)

        self.assertEqual(created["id"], str(REVISION_ID))
        self.assertEqual(snapshot_id, JOB_SNAPSHOT_ID)
        self.assertTrue(http.requests[0]["url"].endswith("/rest/v1/rpc/create_answer_revision"))
        self.assertEqual(
            http.requests[0]["headers"]["Authorization"], "Bearer owner-token"
        )


if __name__ == "__main__":
    unittest.main()
