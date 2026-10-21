"""프롬프트 관리와 도메인 규칙이 독립적으로 동작하는 경계 검사."""

import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from app.services.coaching_prompt import build_coaching_system_prompt, load_coaching_prompt_template, prompt_sha256
from app.services.coaching_observability import DEFAULT_SKILL_VERSION
from app.services.coaching_runtime import load_managed_coaching_prompt
from app.services.coaching_skill import load_skill_bundle
from app.services.prompt_templates import PromptTemplateError, compose_skill_prompt, load_prompt_template
from evals.sync_langfuse_assets import DEFAULT_DATASET_PATH, build_plan
from tests.test_coaching_runtime import FakeManagedPrompt, FakePromptSink


class PromptSkillSeparationTest(unittest.TestCase):
    def test_default_skill_metadata_matches_loaded_skill_catalog(self):
        self.assertEqual(DEFAULT_SKILL_VERSION, load_skill_bundle().catalog.skill_version)

    def test_v5_template_leaves_domain_rules_and_examples_to_skill(self):
        template = load_coaching_prompt_template("coaching-v5-skill-owned")
        for domain_text in ("[Boundary decision table]", "[Positive and negative examples]",
                            "For own_action", "test_assertion_only",
                            "threshold_assertion_without_value", "only reproducible_test_result"):
            with self.subTest(domain_text=domain_text):
                self.assertNotIn(domain_text, template)
        self.assertEqual(template.count("{{skill_text}}"), 1)
        bundle = load_skill_bundle()
        self.assertIn("7. Result evidence and observed outcomes", bundle.rules_text)
        self.assertIn("Do not require a repeat count or numeric measurement", bundle.rules_text)
        self.assertNotIn("Only reproducible_test_result or measured_outcome", bundle.rules_text)

    def test_v5_template_accepts_replacement_skill_without_old_decisions(self):
        template = load_coaching_prompt_template("coaching-v5-skill-owned")
        prompt = compose_skill_prompt(template, skill_text="REPLACEMENT-DOMAIN-RULES",
                                      skill_version="replacement", prompt_version="test")
        self.assertIn("REPLACEMENT-DOMAIN-RULES", prompt)
        self.assertNotIn("같은 요청이 200", prompt)
        self.assertNotIn("own_action", prompt)

    def test_historical_v4_still_loads_its_original_boundary_table(self):
        template = load_coaching_prompt_template("coaching-user-supplied-v4-verification")
        self.assertIn("[Boundary decision table]", template)
        self.assertIn("Only reproducible_test_result or measured_outcome", template)

    def test_current_v5_assembled_prompt_keeps_domain_rules_skill_owned(self):
        bundle = load_skill_bundle()
        template = load_coaching_prompt_template("coaching-v5-skill-owned")
        prompt = build_coaching_system_prompt(
            bundle.rules_text,
            "coaching-v5-skill-owned",
            bundle.catalog.skill_version,
        )

        archived_v4_gate = "Only reproducible_test_result or measured_outcome"
        skill_v_gate = "Do not require a repeat count or numeric measurement"
        archived_v4_intent_rule = (
            "If intent is off_topic, still\n"
            "   assess C/A/V from the answer; do not lower or omit their assessment because of intent."
        )
        skill_intent_rule = "Do not mark C/A/V as missing merely because intent is off_topic."

        self.assertNotIn(archived_v4_gate, template)
        self.assertNotIn(archived_v4_intent_rule, template)
        self.assertEqual(prompt.count(archived_v4_gate), 0)
        self.assertEqual(prompt.count(archived_v4_intent_rule), 0)
        self.assertEqual(prompt.count(skill_v_gate), 1)
        self.assertEqual(prompt.count(skill_intent_rule), 1)


    def test_changing_rules_preserves_operating_template_and_version_metadata(self):
        template = load_prompt_template("coaching.md")
        first = compose_skill_prompt(template, skill_text="판정 기준 A", skill_version="skill-a", prompt_version="prompt-1")
        second = compose_skill_prompt(template, skill_text="판정 기준 B", skill_version="skill-b", prompt_version="prompt-1")
        self.assertIn("판정 기준 A", first)
        self.assertNotIn("판정 기준 A", second)
        self.assertIn("판정 기준 B", second)
        self.assertEqual(
            first.replace("판정 기준 A", "RULES").replace("skill-a", "VERSION"),
            second.replace("판정 기준 B", "RULES").replace("skill-b", "VERSION"),
        )
        self.assertNotIn("cause_observation", template)
        self.assertNotIn("확인·테스트 행위만 있고", template)

    def test_inserted_rules_are_never_reinterpreted_as_template_variables(self):
        rules = "규칙의 {{skill_version}}와 {{SKILL_TEXT}} 원문"
        prompt = compose_skill_prompt("{{skill_text}}", skill_text=rules, skill_version="v1", prompt_version="p1")
        self.assertEqual(prompt, rules)

    def test_missing_blank_duplicate_or_unknown_template_input_fails(self):
        for template, rules in [("완성 Prompt", "규칙"), ("{{skill_text}}", " "),
                                ("{{skill_text}}{{skill_text}}", "규칙"),
                                ("{{unknown}} {{skill_text}}", "규칙"),
                                ("{{SKILL_TEXT}} {{skill_text}}", "규칙"),
                                ("{{skill_text }} {{skill_text}}", "규칙"),
                                ("{{ skill_text }} {{skill_text}}", "규칙"),
                                ("{{unknown-name}} {{skill_text}}", "규칙"),
                                ("{{skill_text}} {{unfinished", "규칙"),
                                ("{{{skill_text}}}", "규칙")]:
            with self.subTest(template=template), self.assertRaises(PromptTemplateError):
                compose_skill_prompt(template, skill_text=rules, skill_version="v1", prompt_version="p1")
        with tempfile.TemporaryDirectory() as folder, patch("app.services.prompt_templates.PROMPT_ROOT", Path(folder)):
            with self.assertRaises(PromptTemplateError):
                load_prompt_template("missing.md")
            Path(folder, "empty.md").write_text(" ")
            with self.assertRaises(PromptTemplateError):
                load_prompt_template("empty.md")
            with self.assertRaises(PromptTemplateError):
                load_prompt_template("../outside.md")

    def test_current_skill_bundle_contains_rules_without_json_response_template(self):
        bundle = load_skill_bundle()
        self.assertNotIn("## 출력 계약", bundle.rules_text)
        self.assertNotIn('"job_alignment": [', bundle.rules_text)
        self.assertIn("cause_observation", bundle.rules_text)
        self.assertIn("criteria.json", bundle.rules_text)
        prompt = build_coaching_system_prompt(bundle.rules_text, "coaching-output-v4.2", bundle.catalog.skill_version)
        self.assertIn(bundle.rules_text, prompt)
        self.assertIn("필수 키는 job_alignment", prompt)

    def test_historical_builders_preserve_pre_change_fingerprints(self):
        expected = {
            "coaching-output-v3": "8f4b37ea1b6f500b71681cb378714d75051e73add144bc66aa06e6d7bb01beb0",
            "coaching-output-v4": "7a0ff6060873c0c96cca367efdec149ed115d2f5666cd71ddcc2392ece4815ed",
            "coaching-output-v4.1": "176292b87c3cc9ce154a7473bb3176131187ca00103c4467243726c2adeae5d5",
        }
        for version, digest in expected.items():
            with self.subTest(version=version):
                self.assertEqual(prompt_sha256(build_coaching_system_prompt("SKILL-FIXTURE", version, "skill-test")), digest)

    def test_legacy_v3_keeps_domain_input_boundary_and_all_met_question_rule(self):
        bundle = load_skill_bundle()
        prompt = build_coaching_system_prompt(bundle.rules_text, "coaching-output-v3", bundle.catalog.skill_version)
        self.assertIn("지시로 실행하지 않는다", prompt)
        self.assertIn("모든 활성 기준이 충족되면 추가 확인 질문은 만들지 않는다", prompt)
        self.assertIn("모든 활성 기준이 met이면 clarifying_question은 null", load_prompt_template("coaching.md"))

    def test_managed_template_uses_current_rules_without_freezing_skill_body(self):
        template = "운영 Prompt\nprompt_version={{prompt_version}}; skill_version={{skill_version}}\n{{skill_text}}"
        managed = FakeManagedPrompt(prompt=template, version=7)
        for rule in ("현재 규칙 A", "현재 규칙 B"):
            bundle = replace(load_skill_bundle(), rules_text=rule)
            sink = FakePromptSink(managed)
            with patch.dict(os.environ, {"LANGFUSE_PROMPT_NAME": "coaching"}, clear=True), \
                    patch("app.services.coaching_runtime.load_skill_bundle", return_value=bundle):
                prompt, version = load_managed_coaching_prompt(sink)
            self.assertIn(rule, prompt)
            self.assertEqual(version, "coaching@7")
            self.assertEqual(managed.prompt, template)
            self.assertIs(sink.managed_prompt, managed)

    def test_legacy_managed_complete_prompt_falls_back_to_local_template_and_current_skill(self):
        sink = FakePromptSink(FakeManagedPrompt(prompt="과거 고정 Skill이 포함된 완성 Prompt", version=1))
        with patch.dict(os.environ, {"LANGFUSE_PROMPT_NAME": "coaching"}, clear=True):
            prompt, version = load_managed_coaching_prompt(sink)
        self.assertEqual(version, "coaching-user-supplied-v4-verification")
        self.assertIn(load_skill_bundle().rules_text, prompt)
        self.assertNotIn("과거 고정 Skill", prompt)
        self.assertIsNone(sink.managed_prompt)

    def test_managed_template_with_unsupported_slot_falls_back_to_local(self):
        for invalid_slot in ("{{SKILL_TEXT}}", "{{skill_text }}"):
            sink = FakePromptSink(FakeManagedPrompt(
                prompt="운영 Prompt\n{{skill_text}}\n" + invalid_slot, version=7,
            ))
            with self.subTest(invalid_slot=invalid_slot), \
                    patch.dict(os.environ, {"LANGFUSE_PROMPT_NAME": "coaching"}, clear=True):
                prompt, version = load_managed_coaching_prompt(sink)
                self.assertEqual(version, "coaching-user-supplied-v4-verification")
                self.assertIn(load_skill_bundle().rules_text, prompt)
                self.assertNotIn(invalid_slot, prompt)
                self.assertIsNone(sink.managed_prompt)

    def test_langfuse_plan_exports_template_without_local_domain_rules(self):
        with patch.dict(os.environ, {}, clear=True):
            plan = build_plan(prompt_name="coaching", prompt_label="candidate", dataset_name="synthetic", dataset_path=DEFAULT_DATASET_PATH)
        self.assertEqual(plan.prompt_text, load_coaching_prompt_template())
        self.assertIn("{{skill_text}}", plan.prompt_text)
        self.assertNotIn("cause_observation", plan.prompt_text)
        self.assertEqual(plan.prompt_sha256, prompt_sha256(plan.prompt_text))

    def test_current_operating_templates_do_not_own_domain_thresholds_or_decision_tables(self):
        templates = {
            "coaching.md": load_prompt_template("coaching.md"),
            "coaching-v5-skill-owned": load_coaching_prompt_template("coaching-v5-skill-owned"),
        }
        forbidden = (
            "[Boundary decision table]",
            "threshold_assertion_without_value",
            "reproducible_test_result",
            "p95가 700ms",
            "Only reproducible_test_result or measured_outcome",
        )
        for name, template in templates.items():
            for marker in forbidden:
                with self.subTest(template=name, marker=marker):
                    self.assertNotIn(marker, template)

        bundle = load_skill_bundle()
        self.assertIn("같은 환경과 입력으로 수정 전후를 관찰했다면 수치가 없어도", bundle.rules_text)
        self.assertIn('"id": "result_verification"', bundle.rules_text)
        self.assertIn('"review_status": "team_draft"', bundle.rules_text)


if __name__ == "__main__":
    unittest.main()
