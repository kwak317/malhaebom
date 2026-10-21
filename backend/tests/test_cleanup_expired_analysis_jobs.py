from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.expired_job_cleanup import cleanup_expired_jobs
from app.services.supabase_persistence import SupabasePersistenceError


class FakeRepository:
    def __init__(self, jobs, failures=()):
        self.jobs, self.failures, self.calls, self.marked = jobs, set(failures), [], []

    def list_expired_jobs(self):
        return self.jobs

    def delete_expired_job(self, job):
        self.calls.extend(["storage-remove", "db-delete"])
        if job["id"] in self.failures:
            self.calls.pop()
            raise SupabasePersistenceError("STORAGE_DELETE_FAILED", "safe")

    def mark_cleanup_failed(self, job_id, code):
        self.marked.append((job_id, code))


class CleanupExpiredJobsTest(unittest.TestCase):
    def test_deletes_storage_before_database_row(self):
        repository = FakeRepository([{"id": "job-1", "audio_path": "u/job-1/original.wav"}])
        summary = cleanup_expired_jobs(repository)
        self.assertEqual(summary.deleted_jobs, 1)
        self.assertEqual(summary.failed_jobs, 0)
        self.assertEqual(repository.calls, ["storage-remove", "db-delete"])

    def test_failure_keeps_row_for_retry_and_records_safe_code(self):
        repository = FakeRepository([{"id": "job-1", "audio_path": "u/job-1/original.wav"}], failures=["job-1"])
        summary = cleanup_expired_jobs(repository)
        self.assertEqual(summary.failed_jobs, 1)
        self.assertEqual(repository.marked, [("job-1", "STORAGE_DELETE_FAILED")])

    def test_empty_expired_list_does_nothing(self):
        repository = FakeRepository([])
        self.assertEqual(cleanup_expired_jobs(repository).deleted_jobs, 0)
        self.assertEqual(repository.calls, [])
