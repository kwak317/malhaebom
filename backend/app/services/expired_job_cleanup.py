from __future__ import annotations

from dataclasses import dataclass

from app.services.supabase_persistence import SupabaseExpiredJobCleanupRepository, SupabasePersistenceError


@dataclass(frozen=True)
class CleanupSummary:
    deleted_jobs: int = 0
    failed_jobs: int = 0


def cleanup_expired_jobs(repository: SupabaseExpiredJobCleanupRepository) -> CleanupSummary:
    deleted = failed = 0
    for job in repository.list_expired_jobs():
        job_id = job.get("id")
        try:
            repository.delete_expired_job(job)
            deleted += 1
        except SupabasePersistenceError as error:
            if isinstance(job_id, str):
                try:
                    repository.mark_cleanup_failed(job_id, error.code)
                except SupabasePersistenceError:
                    pass
            failed += 1
    return CleanupSummary(deleted_jobs=deleted, failed_jobs=failed)
