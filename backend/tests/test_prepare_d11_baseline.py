"""Offline D11 manifest regression tests collected by Product CI (no model calls)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from evals import prepare_d11_baseline as preflight
from app.services.coaching_prompt import DEFAULT_COACHING_PROMPT_VERSION


class D11BaselinePreflightTests(unittest.TestCase):
    def test_manifest_keeps_existing_ground_truth_and_excludes_paid_run(self):
        result = preflight.build_manifest()
        self.assertEqual(result["dataset"]["count"], 30)
        self.assertEqual(result["dataset"]["counts"], {"normal": 12, "boundary": 10, "failure": 8})
        self.assertEqual(len(result["dataset"]["sha256"]), 64)
        self.assertEqual(
            result["proposed_local_candidate"]["skill_version"],
            "interview-coach-v6.2-met-aligned",
        )
        self.assertEqual(
            result["proposed_local_candidate"]["prompt_version"],
            DEFAULT_COACHING_PROMPT_VERSION,
        )
        self.assertEqual(
            set(preflight.SENTINELS),
            {item["case_id"] for item in result["existing_injection_regression_sentinels"]},
        )
        self.assertEqual(result["new_injection_cases_added"], 0)
        self.assertFalse(result["paid_run_authorized"])
        self.assertIsNone(result["official_run_requirements"]["deployed_revision"])

    def test_clean_clone_creates_missing_local_results_and_refuses_overwrite(self):
        # Simulate an entirely fresh clone: do not depend on the real ignored directory.
        with tempfile.TemporaryDirectory() as temp:
            fake_root = Path(temp)
            target = fake_root / "local-results" / "d11-plan"
            self.assertFalse(target.parent.exists())
            manifest = {"status": "OFFLINE_PREFLIGHT_ONLY", "paid_run_authorized": False}
            with (
                patch.object(preflight, "ROOT", fake_root),
                patch.object(preflight, "build_manifest", return_value=manifest),
                patch.object(sys, "argv", ["prepare", "--output-dir", str(target)]),
            ):
                preflight.main()
                self.assertTrue(target.is_dir())
                self.assertEqual(
                    json.loads((target / "preflight.json").read_text(encoding="utf-8")),
                    manifest,
                )
                with self.assertRaises(SystemExit):
                    preflight.main()


if __name__ == "__main__":
    unittest.main()
