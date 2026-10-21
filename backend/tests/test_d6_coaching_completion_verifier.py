from __future__ import annotations

import unittest
import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).with_name("verify_d6_coaching_completion.py")
_SPEC = importlib.util.spec_from_file_location("d6_completion_verifier", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
persistence_matches_request = _MODULE.persistence_matches_request


class D6CoachingCompletionVerifierTests(unittest.TestCase):
    def test_persistence_matches_answer_and_snapshot(self) -> None:
        self.assertTrue(
            persistence_matches_request(
                [
                    {
                        "id": "run-1",
                        "answer_revision_id": "answer-1",
                        "job_snapshot_id": "snapshot-1",
                        "status": "needs_more_info",
                    }
                ],
                answer_revision_id="answer-1",
                job_snapshot_id="snapshot-1",
                previous_run_id=None,
                expected_status="needs_more_info",
            )
        )

    def test_persistence_mismatch_is_rejected(self) -> None:
        self.assertFalse(
            persistence_matches_request(
                [
                    {
                        "id": "run-1",
                        "answer_revision_id": "other-answer",
                        "job_snapshot_id": "snapshot-1",
                        "status": "needs_more_info",
                    }
                ],
                answer_revision_id="answer-1",
                job_snapshot_id="snapshot-1",
                previous_run_id=None,
                expected_status="needs_more_info",
            )
        )

    def test_stale_or_status_mismatched_run_is_rejected(self) -> None:
        row = {"id": "run-1", "answer_revision_id": "answer-1", "job_snapshot_id": "snapshot-1", "status": "ok"}
        self.assertFalse(persistence_matches_request([row], answer_revision_id="answer-1", job_snapshot_id="snapshot-1", previous_run_id="run-1", expected_status="ok"))
        self.assertFalse(persistence_matches_request([row], answer_revision_id="answer-1", job_snapshot_id="snapshot-1", previous_run_id=None, expected_status="needs_more_info"))


if __name__ == "__main__":
    unittest.main()
