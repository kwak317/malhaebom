from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_tracked_artifacts import audit_repository, forbidden_path


class TrackedArtifactPolicyTests(unittest.TestCase):
    def test_detects_secret_filenames_and_model_outputs(self) -> None:
        for path in (
            ".env", ".env.job-source-e2e", ".env.playmcp/auth.json",
            "frontend/.env.production", "credentials.json", "id_ed25519",
            "models/private.safetensors", "data/user.wav",
            "local-results/output.json", "local-results/.env.example",
            "frontend/node_modules/package/index.js",
        ):
            with self.subTest(path=path):
                self.assertTrue(forbidden_path(path))

    def test_allows_examples_and_ordinary_sources(self) -> None:
        for path in (
            ".env.example", "frontend/.env.example",
            "docs/README.md", "docs/experiments/README.md",
            "backend/tests/test_coaching_api.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(forbidden_path(path))

    def test_current_repository_tracking_and_ignore_rules(self) -> None:
        count, findings = audit_repository()
        self.assertGreater(count, 0)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
