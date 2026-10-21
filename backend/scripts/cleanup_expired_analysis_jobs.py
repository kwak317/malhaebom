from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.supabase_settings import SupabaseSettings
from app.services.expired_job_cleanup import cleanup_expired_jobs
from app.services.supabase_persistence import SupabaseExpiredJobCleanupRepository


def main() -> int:
    settings = SupabaseSettings.from_env(require_service_role=True)
    summary = cleanup_expired_jobs(SupabaseExpiredJobCleanupRepository(settings))
    print(f"cleanup completed: deleted={summary.deleted_jobs}, failed={summary.failed_jobs}")
    return 0 if summary.failed_jobs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
