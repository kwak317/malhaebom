from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.tests import run_job_source_e2e as runner


JWT = "header.payload.signature"


class JobSourceE2ERunnerTests(unittest.TestCase):
    def test_env_token_has_priority(self) -> None:
        with patch.dict(
            os.environ,
            {"JOB_SOURCE_E2E_ACCESS_TOKEN": JWT, "D6_ACCESS_TOKEN": ""},
            clear=False,
        ):
            self.assertEqual(runner.resolve_access_token(), JWT)

    @unittest.skipIf(os.name == "nt", "Windows does not expose POSIX file modes")
    def test_reads_private_ignored_token_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            token_file = root / ".env.job-source-e2e"
            token_file.write_text(
                f"JOB_SOURCE_E2E_ACCESS_TOKEN={JWT}\n",
                encoding="utf-8",
            )
            token_file.chmod(0o600)
            with (
                patch.object(runner, "REPO_ROOT", root),
                patch.dict(
                    os.environ,
                    {"JOB_SOURCE_E2E_ACCESS_TOKEN": "", "D6_ACCESS_TOKEN": ""},
                    clear=False,
                ),
            ):
                self.assertEqual(runner.resolve_access_token(), JWT)

    @unittest.skipIf(os.name == "nt", "Windows does not expose POSIX file modes")
    def test_rejects_token_file_with_group_or_other_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            token_file = root / ".env.job-source-e2e"
            token_file.write_text(
                f"JOB_SOURCE_E2E_ACCESS_TOKEN={JWT}\n",
                encoding="utf-8",
            )
            token_file.chmod(0o644)
            with (
                patch.object(runner, "REPO_ROOT", root),
                patch.dict(
                    os.environ,
                    {"JOB_SOURCE_E2E_ACCESS_TOKEN": "", "D6_ACCESS_TOKEN": ""},
                    clear=False,
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "chmod 600"):
                    runner.resolve_access_token()

    def test_requires_environment_token_on_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            token_file = root / ".env.job-source-e2e"
            token_file.write_text(
                f"JOB_SOURCE_E2E_ACCESS_TOKEN={JWT}\n",
                encoding="utf-8",
            )
            with (
                patch.object(runner, "REPO_ROOT", root),
                patch.dict(
                    os.environ,
                    {"JOB_SOURCE_E2E_ACCESS_TOKEN": "", "D6_ACCESS_TOKEN": ""},
                    clear=False,
                ),
                patch.object(runner, "supports_posix_token_file_permissions", return_value=False),
            ):
                with self.assertRaisesRegex(SystemExit, "environment variable"):
                    runner.resolve_access_token()

    def test_requires_environment_token_on_windows_when_token_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(runner, "REPO_ROOT", Path(temp_dir)),
                patch.dict(
                    os.environ,
                    {"JOB_SOURCE_E2E_ACCESS_TOKEN": "", "D6_ACCESS_TOKEN": ""},
                    clear=False,
                ),
                patch.object(runner, "supports_posix_token_file_permissions", return_value=False),
            ):
                with self.assertRaisesRegex(SystemExit, "environment variable"):
                    runner.resolve_access_token()


if __name__ == "__main__":
    unittest.main()
