from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.services.coaching_observability import DEFAULT_PROMPT_VERSION  # noqa: E402
from app.services.coaching_prompt import (  # noqa: E402
    DEFAULT_COACHING_PROMPT_VERSION,
    LEGACY_COACHING_PROMPT_VERSION,
    PROMPT_VERSION_V4,
    PROMPT_VERSION_V41,
    PROMPT_VERSION_V5_REINFORCED_VERIFICATION,
    load_coaching_prompt_template,
    build_coaching_system_prompt,
    build_contract_repair_user_prompt,
    prompt_sha256,
)
from app.services.coaching_runtime import load_fixed_skill_prompt  # noqa: E402
from app.services.coaching_skill import load_skill_bundle  # noqa: E402
from evals.run_model_comparison import build_system_prompt  # noqa: E402


class CoachingPromptHarnessTest(unittest.TestCase):
    def test_default_prompt_version_matches_deployed_v4_everywhere(self):
        self.assertEqual(DEFAULT_COACHING_PROMPT_VERSION, "coaching-user-supplied-v4-verification")
        self.assertEqual(DEFAULT_PROMPT_VERSION, DEFAULT_COACHING_PROMPT_VERSION)

    def test_default_runtime_uses_deployed_v4_template_and_current_skill(self):
        template = (PROJECT_ROOT / "prompts/coaching-user-supplied-v4-verification.md").read_text(encoding="utf-8")
        bundle = load_skill_bundle()
        with patch.dict(os.environ, {}, clear=True):
            prompt = load_fixed_skill_prompt()
        expected = template.replace("{{skill_text}}", bundle.rules_text)
        expected = expected.replace("{{prompt_version}}", DEFAULT_COACHING_PROMPT_VERSION)
        expected = expected.replace("{{skill_version}}", bundle.catalog.skill_version)
        self.assertEqual(prompt, expected)
        self.assertIn("[Boundary decision table]", prompt)
        self.assertIn("가상 긍정·부정 사례", prompt)
        self.assertNotIn("{{skill_text}}", prompt)
        legacy = build_coaching_system_prompt("SKILL", "coaching-output-v4.2", "skill-test")
        self.assertTrue(legacy.startswith("당신은 한국어 면접 답변 코치입니다."))

    def test_blank_version_uses_v4_and_explicit_v5_remains_selectable(self):
        bundle = load_skill_bundle()
        for version in (" ", "coaching-v5-skill-owned"):
            selected = version.strip() or DEFAULT_COACHING_PROMPT_VERSION
            with self.subTest(version=version), patch.dict(
                os.environ, {"COACHING_PROMPT_VERSION": version}, clear=True
            ):
                prompt = load_fixed_skill_prompt()
            self.assertEqual(
                prompt,
                build_coaching_system_prompt(bundle.rules_text, selected, bundle.catalog.skill_version),
            )

    def test_reinforced_v5_preserves_candidate_and_is_explicitly_selectable(self):
        version = PROMPT_VERSION_V5_REINFORCED_VERIFICATION
        template = load_coaching_prompt_template(version)
        self.assertEqual(
            prompt_sha256(template),
            "ed39574026c68be510dad31fb9b8b5077fc92f11848a72c9105f3f16b8bfd9f9",
        )
        bundle = load_skill_bundle()
        with patch.dict(os.environ, {"COACHING_PROMPT_VERSION": version}, clear=True):
            runtime_prompt = load_fixed_skill_prompt()
        self.assertEqual(
            runtime_prompt,
            build_system_prompt(bundle.rules_text, version, bundle.catalog.skill_version),
        )
        self.assertIn(bundle.rules_text, runtime_prompt)
        self.assertNotIn("{{skill_text}}", runtime_prompt)

    def test_prompt_contains_pre_output_harness(self):
        prompt_text = build_coaching_system_prompt(
            "SKILL",
            "policy-test",
            "skill-test",
        )

        for expected in (
            "[출력 전 내부 점검]",
            "정확히 한 번씩 반환",
            "실제로 존재하는 연속 문자열",
            "clarifying_question은 최대 1개",
            "next_actions는 총 1~2개",
            "JSON 객체 하나만",
            "점검 과정이나 체크리스트 자체는 출력하지 마세요",
            "키는 정확히 segment_id와 quote",
            "text 키는 절대 사용하지",
            "evidence 키는 항상 포함",
            "현재 active criterion_id 중 하나만",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, prompt_text)

    def test_runtime_and_evaluation_share_the_same_builder(self):
        bundle = load_skill_bundle()
        environment = {
            "COACHING_PROMPT_VERSION": "policy-test",
            "COACHING_SKILL_VERSION": "skill-test",
        }
        with patch.dict(os.environ, environment, clear=False):
            runtime_prompt = load_fixed_skill_prompt()

        evaluation_prompt = build_system_prompt(
            bundle.rules_text,
            "policy-test",
            "skill-test",
        )
        self.assertEqual(runtime_prompt, evaluation_prompt)

    def test_v3_keeps_legacy_evaluation_prompt_for_reproducibility(self):
        prompt_text = build_system_prompt(
            "SKILL",
            LEGACY_COACHING_PROMPT_VERSION,
            "skill-test",
        )

        self.assertIn("모든 requirement와 criterion을 정확히 한 번씩", prompt_text)
        self.assertNotIn("[출력 전 내부 점검]", prompt_text)

    def test_v4_prompt_is_preserved_for_reproducible_reruns(self):
        prompt_text = build_system_prompt(
            "SKILL",
            PROMPT_VERSION_V4,
            "skill-test",
        )

        self.assertIn("[출력 전 내부 점검]", prompt_text)
        self.assertNotIn("text 키는 절대 사용하지", prompt_text)

    def test_v41_prompt_is_preserved_without_targeted_examples(self):
        prompt_text = build_system_prompt(
            "SKILL",
            PROMPT_VERSION_V41,
            "skill-test",
        )

        self.assertIn("text 키는 절대 사용하지", prompt_text)
        self.assertNotIn("[경계 판정 예시]", prompt_text)

    def test_contract_repair_prompt_includes_previous_output_and_fix_scope(self):
        repaired = build_contract_repair_user_prompt(
            '{"server_context":{"active_criterion_ids":["own_action"]}}',
            {"evidence": [{"segment_id": "s1", "text": "원문"}]},
            ["evidence.0.quote: Field required"],
        )

        self.assertIn("[계약 보정 요청]", repaired)
        self.assertIn('"text": "원문"', repaired)
        self.assertIn("evidence.0.quote: Field required", repaired)
        self.assertIn('"quote": "..."', repaired)
        self.assertIn("새 사실·숫자·역할·기술·성과를 만들지", repaired)

    def test_prompt_hash_is_stable_and_content_sensitive(self):
        prompt = build_coaching_system_prompt("SKILL", "v4", "skill")
        self.assertEqual(prompt_sha256(prompt), prompt_sha256(prompt))
        self.assertNotEqual(
            prompt_sha256(prompt),
            prompt_sha256(prompt + "\nchanged"),
        )
    def test_explicit_v5_prompt_delegates_intent_rule_to_fixed_skill(self):
        bundle = load_skill_bundle()
        prompt = build_coaching_system_prompt(
            skill_text=bundle.rules_text,
            prompt_version="coaching-v5-skill-owned",
            skill_version=bundle.catalog.skill_version,
        )

        self.assertIn(
            "Domain decision rules and judgment\nexamples are owned by that Skill",
            prompt,
        )
        self.assertIn(
            "intent는 현재 답변이 질문에 해당하는 경험을 다루는지만 평가한다.",
            prompt,
        )

if __name__ == "__main__":
    unittest.main()
