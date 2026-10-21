from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import AuthenticatedUser  # noqa: E402
from app.schemas.coaching import CoachingAnalyzeRequest  # noqa: E402
from app.services.coaching_context import (  # noqa: E402
    DEMO_ANSWER_REVISION_ID,
    DEMO_JOB_SNAPSHOT_ID,
    DEMO_QUESTION_ID,
    CoachingContextConflict,
    CoachingContextNotFound,
    build_demo_coaching_service,
)


class CoachingContextServiceTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 17, 2, 0, tzinfo=UTC)
        self.owner = AuthenticatedUser("user-owner", "owner-token")
        self.service = build_demo_coaching_service(
            self.owner.user_id,
            now=self.now,
        ).context_service
        self.request = CoachingAnalyzeRequest(
            action="analyze",
            question_id=DEMO_QUESTION_ID,
            answer_revision_id=DEMO_ANSWER_REVISION_ID,
            job_snapshot_id=DEMO_JOB_SNAPSHOT_ID,
        )

    def test_loads_owned_active_context(self):
        context = self.service.load_context(
            self.owner,
            self.request,
            now=self.now,
        )

        self.assertEqual(context.question.question_id, DEMO_QUESTION_ID)
        self.assertEqual(
            context.practice_attempt.answer_revision_id,
            DEMO_ANSWER_REVISION_ID,
        )
        self.assertEqual(context.job_context.job_snapshot_id, DEMO_JOB_SNAPSHOT_ID)
        self.assertEqual(
            context.to_validation_context().requirement_ids,
            ["J01-R1"],
        )

    def test_hides_other_users_record_as_not_found(self):
        other_user = AuthenticatedUser("user-other", "other-token")

        with self.assertRaises(CoachingContextNotFound):
            self.service.load_context(other_user, self.request, now=self.now)

    def test_hides_expired_record_as_not_found(self):
        with self.assertRaises(CoachingContextNotFound):
            self.service.load_context(
                self.owner,
                self.request,
                now=self.now + timedelta(hours=25),
            )

    def test_rejects_question_that_does_not_match_revision(self):
        mismatched = self.request.model_copy(update={"question_id": "preset-05"})

        with self.assertRaises(CoachingContextConflict):
            self.service.load_context(self.owner, mismatched, now=self.now)

    def test_rejects_job_context_from_another_session(self):
        record = self.service.repository.job_contexts[DEMO_JOB_SNAPSHOT_ID]
        self.service.repository.job_contexts[DEMO_JOB_SNAPSHOT_ID] = record.model_copy(
            update={
                "practice_session_id": UUID(
                    "00000000-0000-0000-0000-000000000999"
                )
            }
        )

        with self.assertRaises(CoachingContextConflict):
            self.service.load_context(self.owner, self.request, now=self.now)

    def test_hides_job_context_owned_by_another_user(self):
        record = self.service.repository.job_contexts[DEMO_JOB_SNAPSHOT_ID]
        self.service.repository.job_contexts[DEMO_JOB_SNAPSHOT_ID] = record.model_copy(
            update={"user_id": "user-other"}
        )

        with self.assertRaises(CoachingContextNotFound):
            self.service.load_context(self.owner, self.request, now=self.now)

    def test_hides_expired_job_context(self):
        record = self.service.repository.job_contexts[DEMO_JOB_SNAPSHOT_ID]
        self.service.repository.job_contexts[DEMO_JOB_SNAPSHOT_ID] = record.model_copy(
            update={"expires_at": self.now - timedelta(seconds=1)}
        )

        with self.assertRaises(CoachingContextNotFound):
            self.service.load_context(self.owner, self.request, now=self.now)

    def test_rejects_job_context_pending_review(self):
        record = self.service.repository.job_contexts[DEMO_JOB_SNAPSHOT_ID]
        self.service.repository.job_contexts[DEMO_JOB_SNAPSHOT_ID] = record.model_copy(
            update={"review_status": "pending"}
        )

        with self.assertRaises(CoachingContextConflict):
            self.service.load_context(self.owner, self.request, now=self.now)


if __name__ == "__main__":
    unittest.main()
