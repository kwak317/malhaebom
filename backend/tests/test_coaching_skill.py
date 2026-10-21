from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.schemas.coaching import QuestionContext  # noqa: E402
from app.services.coaching_skill import (  # noqa: E402
    CoachingSkillError,
    load_skill_bundle,
)
from evals.coaching_dataset import load_dataset  # noqa: E402


class CoachingSkillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_skill_bundle()

    def test_bundle_has_canonical_draft_contract(self):
        self.assertEqual(self.bundle.catalog.skill_version, "interview-coach-v6")
        self.assertEqual(
            self.bundle.catalog.criteria_version,
            "problem-solving-v4-draft.3",
        )
        self.assertEqual(self.bundle.catalog.review_status, "team_draft")
        self.assertEqual(
            set(self.bundle.catalog.question_types["problem_solving"].allowed_criterion_ids),
            {
                "problem_context",
                "cause_observation",
                "cause_inference",
                "own_action",
                "action_rationale",
                "result_verification",
            },
        )
        self.assertIn("[problem-solving.md]", self.bundle.rules_text)
        self.assertNotIn("# {도메인} Skill", self.bundle.rules_text)
        self.assertEqual(len(self.bundle.sha256), 64)

    def test_catalog_splits_cause_observation_and_inference(self):
        criteria = {item.id: item for item in self.bundle.catalog.criteria}

        self.assertIn("cause_observation", criteria)
        self.assertIn("cause_inference", criteria)
        self.assertNotIn("cause_reasoning", criteria)
        self.assertIn("구체적 신호", criteria["cause_observation"].met)
        self.assertIn("원인 후보", criteria["cause_inference"].met)
        self.assertIn("로그를 봤다", self.bundle.rules_text)

    def test_question_context_must_match_catalog(self):
        valid = QuestionContext(
            question_id="preset-04",
            text="문제 해결 경험을 말씀해주세요.",
            question_type="problem_solving",
            active_criterion_ids=["problem_context", "own_action"],
            criteria_version="problem-solving-v4-draft.3",
        )
        self.bundle.validate_question_context(valid)

        invalid = valid.model_copy(update={"criteria_version": "old-version"})
        with self.assertRaises(CoachingSkillError):
            self.bundle.validate_question_context(invalid)

    def test_evaluation_cases_use_only_catalog_criteria(self):
        cases = load_dataset(PROJECT_ROOT / "evals" / "dataset.jsonl")
        for case in cases:
            with self.subTest(case=case.id):
                self.assertLessEqual(
                    set(case.context.active_criterion_ids),
                    self.bundle.criterion_ids,
                )

    def test_rule_provenance_covers_every_criterion_and_records_confirmed_review(self):
        candidate_dir = PROJECT_ROOT / "evals/candidates/main-before-production-sync-20261010/skills/interview-coach"
        candidate = load_skill_bundle(candidate_dir / "SKILL.md")
        path = candidate_dir / "rule-provenance.json"
        provenance = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(provenance["skill_version"], candidate.catalog.skill_version)
        self.assertEqual(
            provenance["criteria_version"],
            candidate.catalog.criteria_version,
        )
        self.assertEqual(set(provenance["entries"]), candidate.criterion_ids)

        confirmation = provenance["expert_review_confirmation"]
        self.assertEqual(confirmation["reviewer"], "김창민")
        self.assertEqual(confirmation["information_source"], "사용자 제공")
        self.assertTrue(confirmation["confirmation_source"].strip())
        self.assertEqual(confirmation["recorded_on"], "2026-10-09")
        self.assertEqual(len(provenance["entries"]), 33)

        criteria = {item.id: item for item in candidate.catalog.criteria}
        for criterion_id, entry in provenance["entries"].items():
            with self.subTest(criterion_id=criterion_id):
                self.assertEqual(entry["rationale"], criteria[criterion_id].description)
                self.assertTrue(
                    (path.parent / entry["source"]["path"]).is_file(),
                    entry["source"]["path"],
                )
                self.assertEqual(entry["expert_review"]["status"], "reviewed")
                self.assertEqual(entry["expert_review"]["display_status"], "김창민 검토 완료")
                self.assertEqual(entry["expert_review"]["reviewer"], "김창민")
                self.assertEqual(entry["expert_review"]["confirmation_source"], "user_confirmation")
                self.assertTrue(entry["expert_review"]["reason"].strip())


if __name__ == "__main__":
    unittest.main()
