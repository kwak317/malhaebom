from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from evals.run_single_skill_rule_comparison import (  # noqa: E402
    DEFAULT_SPEC,
    build_plan,
    build_rule_variants,
    changed_lines,
    evaluate_decision,
    load_candidate_spec,
    main,
)


class SingleSkillRuleComparisonTest(unittest.TestCase):
    def test_candidate_changes_exactly_one_rule_line(self):
        spec = load_candidate_spec(DEFAULT_SPEC)
        bundle, candidate_rules = build_rule_variants(spec)

        removed, added = changed_lines(bundle.rules_text, candidate_rules)

        self.assertEqual(removed, [spec["old_rule"]])
        self.assertEqual(added, [spec["new_rule"]])
        self.assertEqual(spec["target_case"], "coach-boundary-19")

    def test_plan_locks_everything_except_one_skill_rule(self):
        spec = load_candidate_spec(DEFAULT_SPEC)
        bundle, candidate_rules = build_rule_variants(spec)

        plan = build_plan(
            spec,
            bundle,
            candidate_rules,
            repeats=2,
            case_ids=[],
        )

        self.assertEqual(plan["repeats"], 2)
        self.assertEqual(plan["single_variable_contract"]["changed"], "one Skill rule line only")
        self.assertEqual(plan["locked"]["dataset"], "evals/dataset.v2.jsonl")
        self.assertEqual(plan["locked"]["prompt_version"], "coaching-v5-skill-owned")
        self.assertEqual(plan["locked"]["model"], "google/gemini-3.5-flash-lite")
        self.assertEqual(
            plan["target_criteria"],
            ["problem_context", "own_action", "result_verification"],
        )
        self.assertNotEqual(
            plan["baseline"]["system_prompt_sha256"],
            plan["candidate"]["system_prompt_sha256"],
        )
        self.assertEqual(
            plan["baseline"]["skill_version"],
            plan["candidate"]["skill_version_metadata"],
        )

    def test_candidate_spec_is_json_roundtrip_stable(self):
        spec = load_candidate_spec(DEFAULT_SPEC)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "spec.json"
            path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
            self.assertEqual(load_candidate_spec(path), spec)

    def test_dry_run_writes_plan_without_provider_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "dry-run"
            argv = [
                "run_single_skill_rule_comparison.py",
                "--output-dir",
                str(output),
                "--case-id",
                "coach-boundary-19",
                "--dry-run",
            ]
            with patch.object(sys, "argv", argv):
                main()
            plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["selected_cases"], ["coach-boundary-19"])
            self.assertEqual(plan["single_variable_contract"]["changed"], "one Skill rule line only")
            self.assertTrue((output / "baseline.system.txt").is_file())
            self.assertTrue((output / "candidate.system.txt").is_file())

    def test_decision_uses_all_target_cav_criteria_not_problem_context_only(self):
        spec = load_candidate_spec(DEFAULT_SPEC)
        report = {
            "candidates": {
                "baseline": {
                    "final_contract_rate": 1.0,
                    "metrics": {"label_accuracy": 0.8},
                },
                "candidate": {
                    "final_contract_rate": 1.0,
                    "metrics": {"label_accuracy": 0.8},
                },
            },
            "attempts": [
                {
                    "candidate": "baseline",
                    "case_id": "coach-boundary-19",
                    "score": {
                        "label_results": {
                            "criterion:problem_context": True,
                            "criterion:own_action": False,
                            "criterion:result_verification": False,
                        }
                    },
                },
                {
                    "candidate": "candidate",
                    "case_id": "coach-boundary-19",
                    "score": {
                        "label_results": {
                            "criterion:problem_context": True,
                            "criterion:own_action": True,
                            "criterion:result_verification": True,
                        }
                    },
                },
            ],
        }

        decision = evaluate_decision(report, spec)

        self.assertEqual(decision["target_hits"]["baseline"], 1)
        self.assertEqual(decision["target_hits"]["candidate"], 3)
        self.assertEqual(
            decision["target_hits_by_criterion"]["candidate"],
            {
                "problem_context": 1,
                "own_action": 1,
                "result_verification": 1,
            },
        )
        self.assertEqual(
            decision["recommendation"],
            "KEEP_CANDIDATE_PENDING_HUMAN_REVIEW",
        )

    def test_decision_rejects_target_regression_even_when_total_hits_improve(self):
        spec = load_candidate_spec(DEFAULT_SPEC)
        report = {
            "candidates": {
                "baseline": {
                    "final_contract_rate": 1.0,
                    "metrics": {"label_accuracy": 0.8},
                },
                "candidate": {
                    "final_contract_rate": 1.0,
                    "metrics": {"label_accuracy": 0.8},
                },
            },
            "attempts": [
                {
                    "candidate": "baseline",
                    "case_id": "coach-boundary-19",
                    "score": {
                        "label_results": {
                            "criterion:problem_context": True,
                            "criterion:own_action": False,
                            "criterion:result_verification": False,
                        }
                    },
                },
                {
                    "candidate": "baseline",
                    "case_id": "coach-boundary-19",
                    "score": {
                        "label_results": {
                            "criterion:problem_context": True,
                            "criterion:own_action": False,
                            "criterion:result_verification": False,
                        }
                    },
                },
                {
                    "candidate": "candidate",
                    "case_id": "coach-boundary-19",
                    "score": {
                        "label_results": {
                            "criterion:problem_context": True,
                            "criterion:own_action": True,
                            "criterion:result_verification": True,
                        }
                    },
                },
                {
                    "candidate": "candidate",
                    "case_id": "coach-boundary-19",
                    "score": {
                        "label_results": {
                            "criterion:problem_context": False,
                            "criterion:own_action": True,
                            "criterion:result_verification": True,
                        }
                    },
                },
            ],
        }

        decision = evaluate_decision(report, spec)

        self.assertGreater(
            decision["target_hits"]["candidate"],
            decision["target_hits"]["baseline"],
        )
        self.assertEqual(decision["target_deltas_by_criterion"]["problem_context"], -1)
        self.assertFalse(decision["no_target_regression"])
        self.assertEqual(decision["recommendation"], "DISCARD_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
