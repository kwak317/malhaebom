from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import AuthenticatedUser  # noqa: E402
from app.core.supabase_settings import SupabaseSettings  # noqa: E402
from app.services.attempt_comparison import (  # noqa: E402
    AttemptComparisonConflict,
    AttemptComparisonNotFound,
    AttemptComparisonService,
)
from app.services.supabase_attempt_comparison import (  # noqa: E402
    SupabaseAttemptComparisonRepository,
)


PREVIOUS_RUN_ID = UUID("a0000000-0000-4000-8000-000000000001")
CURRENT_RUN_ID = UUID("a0000000-0000-4000-8000-000000000002")
USER = AuthenticatedUser("user-owner", "owner-access-token")


def run_row(
    run_id: UUID,
    attempt_no: int,
    *,
    user_id: str = USER.user_id,
    practice_session_id: str = "90000000-0000-4000-8000-000000000001",
    question_id: str = "preset-04",
    job_snapshot_id: str = "80000000-0000-4000-8000-000000000001",
    model_name: str = "model-a",
    prompt_version: str = "prompt-v1",
    skill_version: str = "skill-v1",
    expires_at: datetime | None = None,
) -> dict[str, object]:
    expiry = (expires_at or datetime.now(UTC) + timedelta(hours=1)).isoformat()
    if attempt_no == 1:
        transcript = "로그인 오류가 발생했고 수정 후 결과는 확인하지 못했습니다."
        assessments = [
            {
                "criterion_id": "problem_context",
                "assessment": "partial",
                "reason": "문제는 있지만 발생 조건이 부족합니다.",
                "evidence": [
                    {"segment_id": "first-s1", "quote": "로그인 오류가 발생했고"}
                ],
                "needed": "발생 조건",
            },
            {
                "criterion_id": "result_verification",
                "assessment": "not_observed",
                "reason": "결과 확인을 관찰하지 못했습니다.",
                "evidence": [],
                "needed": "확인 방법과 결과",
            },
        ]
        metrics = {"cpm": 330, "long_silence_count": 2, "repetition_count": 1}
    else:
        transcript = "공백 입력에서 로그인 오류를 재현했고 수정 후 두 입력 모두 성공을 확인했습니다."
        assessments = [
            {
                "criterion_id": "problem_context",
                "assessment": "met",
                "reason": "문제와 발생 조건을 설명했습니다.",
                "evidence": [
                    {
                        "segment_id": "second-s1",
                        "quote": "공백 입력에서 로그인 오류를 재현했고",
                    }
                ],
                "needed": None,
            },
            {
                "criterion_id": "result_verification",
                "assessment": "met",
                "reason": "수정 후 확인 결과를 설명했습니다.",
                "evidence": [
                    {
                        "segment_id": "second-s2",
                        "quote": "수정 후 두 입력 모두 성공을 확인했습니다.",
                    }
                ],
                "needed": None,
            },
        ]
        metrics = {"cpm": 300, "long_silence_count": 1, "repetition_count": 1}
    return {
        "id": str(run_id),
        "user_id": user_id,
        "answer_revision_id": f"70000000-0000-4000-8000-00000000000{attempt_no}",
        "job_snapshot_id": job_snapshot_id,
        "status": "ok",
        "response": {
            "status": "ok",
            "criterion_assessments": assessments,
        },
        "model_name": model_name,
        "prompt_version": prompt_version,
        "skill_version": skill_version,
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": expiry,
        "answer_revisions": {
            "id": f"70000000-0000-4000-8000-00000000000{attempt_no}",
            "user_id": user_id,
            "practice_session_id": practice_session_id,
            "question_id": question_id,
            "confirmed_text": transcript,
            "delivery_metrics": metrics,
            "expires_at": expiry,
            "analysis_jobs": {
                "attempt_no": attempt_no,
                "status": "completed",
                "expires_at": expiry,
            },
        },
    }


class FakeRepository:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[dict[str, object]] = []

    def get_coaching_runs(self, **kwargs):
        self.calls.append(kwargs)
        return deepcopy(self.rows)


class AttemptComparisonServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeRepository(
            [run_row(PREVIOUS_RUN_ID, 1), run_row(CURRENT_RUN_ID, 2)]
        )
        self.service = AttemptComparisonService(self.repository)

    def compare(self):
        return self.service.compare(
            USER,
            previous_coaching_run_id=PREVIOUS_RUN_ID,
            current_coaching_run_id=CURRENT_RUN_ID,
        )

    def test_compares_saved_runs_without_exposing_transcripts(self):
        result = self.compare()

        comparison = result["comparison"]
        self.assertTrue(comparison["content_available"])
        self.assertEqual(
            [item["criterion_id"] for item in comparison["added_explanations"]],
            ["result_verification"],
        )
        self.assertEqual(comparison["criteria"][0]["change"], "changed")
        self.assertEqual(comparison["criteria"][1]["change"], "added")
        self.assertEqual(comparison["delivery"]["cpm"]["direction"], "decreased")
        self.assertEqual(
            comparison["delivery"]["repetition_count"]["direction"], "same"
        )
        self.assertNotIn("confirmed_text", result)
        self.assertNotIn("transcript", str(result))
        self.assertEqual(self.repository.calls[0]["user_id"], USER.user_id)

    def test_rejects_owner_or_expired_run_as_not_found(self):
        other_owner = run_row(CURRENT_RUN_ID, 2, user_id="user-other")
        self.repository.rows = [run_row(PREVIOUS_RUN_ID, 1), other_owner]
        with self.assertRaises(AttemptComparisonNotFound):
            self.compare()

        expired = run_row(
            CURRENT_RUN_ID,
            2,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        self.repository.rows = [run_row(PREVIOUS_RUN_ID, 1), expired]
        with self.assertRaises(AttemptComparisonNotFound):
            self.compare()

    def test_rejects_different_session_or_generation_settings(self):
        different_session = run_row(
            CURRENT_RUN_ID,
            2,
            practice_session_id="90000000-0000-4000-8000-000000000099",
        )
        self.repository.rows = [run_row(PREVIOUS_RUN_ID, 1), different_session]
        with self.assertRaisesRegex(AttemptComparisonConflict, "practice_session_id"):
            self.compare()

        different_prompt = run_row(CURRENT_RUN_ID, 2, prompt_version="prompt-v2")
        self.repository.rows = [run_row(PREVIOUS_RUN_ID, 1), different_prompt]
        with self.assertRaisesRegex(AttemptComparisonConflict, "prompt_version"):
            self.compare()

        different_skill = run_row(CURRENT_RUN_ID, 2, skill_version="interview-coach-v4")
        self.repository.rows = [run_row(PREVIOUS_RUN_ID, 1), different_skill]
        with self.assertRaisesRegex(AttemptComparisonConflict, "skill_version"):
            self.compare()

    def test_rejects_reversed_attempt_order(self):
        self.repository.rows = [
            run_row(PREVIOUS_RUN_ID, 2),
            run_row(CURRENT_RUN_ID, 1),
        ]

        with self.assertRaisesRegex(AttemptComparisonConflict, "1차"):
            self.compare()


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class FakeHttp:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    def get(self, url: str, **kwargs):
        self.requests.append({"url": url, **kwargs})
        return self.response


class SupabaseAttemptComparisonRepositoryTest(unittest.TestCase):
    def test_query_is_owner_and_expiry_scoped_with_server_secret(self):
        http = FakeHttp(FakeResponse(200, [{"id": str(PREVIOUS_RUN_ID)}]))
        repository = SupabaseAttemptComparisonRepository(
            SupabaseSettings("https://project.supabase.co", "publishable", "secret"),
            http,
        )

        rows = repository.get_coaching_runs(
            user_id=USER.user_id,
            previous_coaching_run_id=PREVIOUS_RUN_ID,
            current_coaching_run_id=CURRENT_RUN_ID,
        )

        self.assertEqual(rows[0]["id"], str(PREVIOUS_RUN_ID))
        request = http.requests[0]
        self.assertIn(f"id=in.({PREVIOUS_RUN_ID},{CURRENT_RUN_ID})", request["url"])
        self.assertIn("user_id=eq.user-owner", request["url"])
        self.assertIn("expires_at=gt.", request["url"])
        self.assertIn("answer_revisions!inner", request["url"])
        self.assertEqual(request["headers"]["Authorization"], "Bearer secret")


if __name__ == "__main__":
    unittest.main()
