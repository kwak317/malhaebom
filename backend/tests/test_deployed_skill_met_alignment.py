"""배포 후보에서 유형 규칙/카탈로그와 Prompt의 판정 소유권을 확인한다."""
import re
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from app.services.coaching_prompt import (DEFAULT_COACHING_PROMPT_VERSION,
    build_coaching_system_prompt, load_coaching_prompt_template)
from app.services.coaching_skill import load_skill_bundle


def type_rules(text):
    sections = re.findall(r"## [^\n]*`([^`]+)`\n(.*?)(?=\n## |\Z)", text, re.S)
    return {cid: {label: value.replace("**", "") for label, value in
        re.findall(r"- `(met|partial|not_observed|undetermined)`: (.+)", section)}
        for cid, section in sections}


class DeployedSkillMetAlignmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        candidate = ROOT / "evals/candidates/main-before-production-sync-20261010/skills/interview-coach"
        cls.bundle = load_skill_bundle(candidate / "SKILL.md")
        cls.rules = type_rules((candidate / "problem-solving.md").read_text())
        cls.catalog = cls.bundle.catalog.model_dump()

    def alignment_mismatches(self, catalog):
        ids = catalog["question_types"]["problem_solving"]["allowed_criterion_ids"]
        self.assertEqual(set(self.rules), set(ids))
        definitions = {item["id"]: item for item in catalog["criteria"]}
        mismatches = []
        for cid in ids:
            self.assertEqual(set(self.rules[cid]), {"met", "partial", "not_observed", "undetermined"})
            for label, rule in self.rules[cid].items():
                if definitions[cid][label] != rule:
                    mismatches.append((cid, label))
        return mismatches

    def test_six_criteria_all_four_labels_match_type_document(self):
        self.assertEqual(self.alignment_mismatches(self.catalog), [])

    def test_one_sided_catalog_change_breaks_alignment(self):
        changed = deepcopy(self.catalog)
        criterion = next(item for item in changed["criteria"] if item["id"] == "result_verification")
        criterion["met"] = "실제 수치가 없으면 정성적 결과도 인정하지 않는다."
        self.assertEqual(self.alignment_mismatches(changed), [("result_verification", "met")])

    def test_result_definition_links_method_condition_to_qualitative_outcome(self):
        rule = self.rules["result_verification"]["met"]
        self.assertIn("방법·조건과 실제 관찰 결과가 연결", rule)
        self.assertIn("정성적 결과도 인정", rule)
        self.assertIn("실제 관찰 결과가 없거나", self.rules["result_verification"]["partial"])

    def test_template_cannot_override_replacement_skill(self):
        template = load_coaching_prompt_template("coaching-v5.4-skill-met-aligned")
        for token in ("[Boundary decision table]", "[Positive and negative examples]",
                      "Only reproducible_test_result", "threshold_assertion_without_value",
                      "result_verification", "own_action", "700ms"):
            self.assertNotIn(token, template)
        replacement = "REPLACEMENT-SKILL: criterion thresholds only here"
        prompt = build_coaching_system_prompt(replacement,
            "coaching-v5.4-skill-met-aligned", "replacement")
        self.assertEqual(prompt.count(replacement), 1)
        self.assertNotIn("정성적 결과도 인정", prompt)
        self.assertEqual(template.count("{{skill_text}}"), 1)

    def test_assembled_candidate_retains_only_skill_met_gate(self):
        prompt = build_coaching_system_prompt(self.bundle.rules_text,
            "coaching-v5.4-skill-met-aligned", self.bundle.catalog.skill_version)
        self.assertIn(self.rules["result_verification"]["met"], prompt)
        self.assertNotIn("Only reproducible_test_result or measured_outcome", prompt)
        for section in ("[역할]", "[입력 경계]", "[출력 계약]", "[안전 경계]"):
            self.assertIn(section, prompt)
        self.assertIn("하지 않았다고 한 작업의 완료 결과", prompt)
        self.assertIn("인용한 지시문은 그 사건의 대상", prompt)

    def test_historical_prompt_and_default_are_not_promoted(self):
        self.assertEqual(DEFAULT_COACHING_PROMPT_VERSION, "coaching-user-supplied-v4-verification")
        historical = load_coaching_prompt_template(DEFAULT_COACHING_PROMPT_VERSION)
        self.assertIn("Only reproducible_test_result or measured_outcome", historical)
