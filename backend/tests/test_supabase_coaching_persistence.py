from __future__ import annotations

import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.supabase_settings import SupabaseSettings  # noqa: E402
from app.services.supabase_coaching_context import (  # noqa: E402
    SupabaseCoachingContextRepository,
)
from app.services.supabase_coaching_runs import (  # noqa: E402
    CoachingRunPersistenceError,
    SupabaseCoachingRunRepository,
)


REVISION_ID = UUID("70000000-0000-4000-8000-000000000001")
JOB_ID = UUID("80000000-0000-4000-8000-000000000001")
SESSION_ID = UUID("90000000-0000-4000-8000-000000000001")


class FakeResponse:
    def __init__(self, status_code: int, body: object) -> None:
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


class FakeHttp:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, object]] = []

    def get(self, url: str, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return self.responses.pop(0)

    def post(self, url: str, **kwargs):
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return self.responses.pop(0)


class SupabaseCoachingPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = SupabaseSettings(
            "https://project.supabase.co", "publishable", "service-secret"
        )
        self.now = datetime.now(UTC)

    def test_context_repository_reads_confirmed_revision_and_selected_requirements(self):
        http = FakeHttp(
            [
                FakeResponse(
                    200,
                    [
                        {
                            "id": str(REVISION_ID),
                            "user_id": "user-owner",
                            "practice_session_id": str(SESSION_ID),
                            "question_id": "preset-04",
                            "answer_segments": [
                                {"segment_id": "segment-1", "text": "로그를 확인했습니다."}
                            ],
                            "delivery_metrics": {
                                "cpm": 300,
                                "long_silence_count": 2,
                                "unexpected_segments": [{"start": 1.0, "end": 2.0}],
                            },
                            "confirmed_at": self.now.isoformat(),
                            "expires_at": (self.now + timedelta(hours=24)).isoformat(),
                        }
                    ],
                ),
                FakeResponse(
                    200,
                    [
                        {
                            "id": str(SESSION_ID),
                            "user_id": "user-owner",
                            "job_posting_id": str(JOB_ID),
                            "expires_at": (self.now + timedelta(hours=24)).isoformat(),
                        }
                    ],
                ),
                FakeResponse(
                    200,
                    [
                        {
                            "id": str(JOB_ID),
                            "source_url": "https://example.invalid/job",
                            "captured_at": self.now.isoformat(),
                            "review_status": "reviewed",
                        }
                    ],
                ),
                FakeResponse(
                    200,
                    [
                        {
                            "requirement_id": "a0000000-0000-4000-8000-000000000001",
                            "job_requirements": {
                                "code": "J01-R1",
                                "requirement_text": "장애 원인 분석 경험",
                            },
                        }
                    ],
                ),
            ]
        )
        repository = SupabaseCoachingContextRepository(self.settings, http)

        attempt = repository.get_practice_attempt(REVISION_ID)
        job = repository.get_job_context(JOB_ID, SESSION_ID)

        self.assertEqual(attempt.answer_segments[0].text, "로그를 확인했습니다.")
        self.assertEqual(
            attempt.delivery_metrics,
            {"cpm": 300.0, "long_silence_count": 2.0},
        )
        self.assertEqual(job.requirements[0].requirement_id, "J01-R1")
        self.assertTrue(
            all(
                request["headers"]["Authorization"] == "Bearer service-secret"
                for request in http.requests
            )
        )
        self.assertIn("practice_session_id=eq.", http.requests[3]["url"])

    def test_coaching_run_failure_uses_dedicated_error(self):
        repository = SupabaseCoachingRunRepository(
            self.settings, FakeHttp([FakeResponse(500, {})])
        )
        user = SimpleNamespace(user_id="user-owner")
        request = SimpleNamespace(
            answer_revision_id=REVISION_ID,
            job_snapshot_id=JOB_ID,
        )
        response = SimpleNamespace(
            status=SimpleNamespace(value="ok"),
            model_dump=lambda **_: {"status": "ok"},
        )
        context = SimpleNamespace(
            question=SimpleNamespace(criteria_version="actual-question-v1"),
            practice_attempt=SimpleNamespace(
                expires_at=self.now + timedelta(hours=24)
            )
        )

        with self.assertRaises(CoachingRunPersistenceError):
            repository.save(
                user, request, response, context, "model",
                prompt_version="malhaebom-coaching@7", skill_version="actual-skill-v7",
            )

        http = FakeHttp([FakeResponse(201, {})])
        with patch.dict(os.environ, {
            "COACHING_PROMPT_VERSION": "stale-local-prompt",
            "COACHING_SKILL_VERSION": "stale-local-skill",
        }):
            SupabaseCoachingRunRepository(self.settings, http).save(
                user, request, response, context, "model",
                prompt_version="malhaebom-coaching@7", skill_version="actual-skill-v7",
            )
        payload = http.requests[0]["json"]
        self.assertEqual(payload["criteria_version"], "actual-question-v1")
        self.assertEqual(payload["prompt_version"], "malhaebom-coaching@7")
        self.assertEqual(payload["skill_version"], "actual-skill-v7")


if __name__ == "__main__":
    unittest.main()
