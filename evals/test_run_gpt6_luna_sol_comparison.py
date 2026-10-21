from __future__ import annotations

import unittest
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.run_gpt6_luna_sol_comparison import (
    CANDIDATES,
    MAX_CALLS,
    OPENROUTER_BASE_URL,
    PREFLIGHT_CASES,
    PROMPT_VERSION,
    build_command,
    main,
)


class Gpt6CandidateComparisonTest(unittest.TestCase):
    def test_preflight_command_freezes_models_prompt_and_cases(self):
        command = build_command("preflight", Path("/tmp/gpt6-preflight"))

        self.assertEqual(command.count("--candidate"), len(CANDIDATES))
        for candidate in CANDIDATES:
            self.assertIn(candidate, command)
        self.assertIn(PROMPT_VERSION, command)
        self.assertEqual(command.count("--case-id"), len(PREFLIGHT_CASES))
        for case_id in PREFLIGHT_CASES:
            self.assertIn(case_id, command)
        self.assertIn(str(MAX_CALLS), command)

    def test_full_command_uses_all_dataset_cases(self):
        command = build_command("full", Path("/tmp/gpt6-full"))

        self.assertNotIn("--case-id", command)
        self.assertIn("dataset.v2.jsonl", " ".join(command))

    @patch("evals.run_gpt6_luna_sol_comparison.subprocess.run")
    @patch(
        "sys.argv",
        ["run_gpt6_luna_sol_comparison.py", "--phase", "preflight"],
    )
    def test_default_mode_does_not_make_network_calls(self, run_mock):
        self.assertEqual(main(), 0)
        run_mock.assert_not_called()

    @patch("evals.run_gpt6_luna_sol_comparison.subprocess.run")
    @patch(
        "sys.argv",
        ["run_gpt6_luna_sol_comparison.py", "--phase", "preflight", "--live"],
    )
    def test_live_mode_forces_openrouter_endpoint(self, run_mock):
        run_mock.return_value.returncode = 0

        self.assertEqual(main(), 0)

        child_env = run_mock.call_args.kwargs["env"]
        self.assertEqual(child_env["MODEL_API_BASE_URL"], OPENROUTER_BASE_URL)


if __name__ == "__main__":
    unittest.main()
