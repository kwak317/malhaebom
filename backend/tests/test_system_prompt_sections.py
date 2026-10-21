from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.schemas.job_search_intent import JobSearchIntentRequest  # noqa: E402
from app.services.job_search_intent import JobSearchIntentService  # noqa: E402
from app.services.prompt_templates import load_prompt_template  # noqa: E402
from app.services.question_rubric_generator import (  # noqa: E402
    _evaluation_prompt,
    _example_answer_prompt,
    _generation_prompt,
)


REQUIRED_SECTIONS = ("[역할]", "[입력 경계]", "[출력 계약]", "[안전 경계]")


class _FakeIntentProvider:
    model_name = "test-model"

    def __init__(self) -> None:
        self.request = None

    def generate(self, **kwargs):
        self.request = kwargs
        return {"should_search": False, "query": None}


def assert_standard_sections(test: unittest.TestCase, prompt: str) -> None:
    positions = []
    for section in REQUIRED_SECTIONS:
        test.assertEqual(prompt.count(section), 1, section)
        positions.append(prompt.index(section))
    test.assertEqual(positions, sorted(positions))


class SystemPromptSectionContractTest(unittest.TestCase):
    def test_mutable_prompt_templates_use_standard_sections(self):
        for name in (
            "github-readme-analysis.md",
            "job-requirement-analysis.md",
            "interview-conversation.md",
            "coaching-v5-skill-owned.md",
        ):
            with self.subTest(name=name):
                assert_standard_sections(self, load_prompt_template(name))

    def test_question_rubric_prompts_use_standard_sections(self):
        rubric = {
            "question": "문제 해결 경험을 말해 주세요.",
            "required_concepts": [
                {"id": "problem", "description": "문제 상황"},
                {"id": "action", "description": "본인의 행동"},
                {"id": "result", "description": "확인한 결과"},
            ],
        }
        for name, prompt in (
            ("generation", _generation_prompt()),
            ("evaluation", _evaluation_prompt(rubric)),
            ("example", _example_answer_prompt()),
        ):
            with self.subTest(name=name):
                assert_standard_sections(self, prompt)

    def test_job_search_intent_prompt_uses_standard_sections(self):
        provider = _FakeIntentProvider()
        JobSearchIntentService(provider).classify(
            JobSearchIntentRequest(message="면접 준비 도와줘")
        )
        assert_standard_sections(self, provider.request["system_prompt"])
        self.assertIn("[사용자 메시지 시작]", provider.request["user_prompt"])
        self.assertIn("[사용자 메시지 끝]", provider.request["user_prompt"])

    def test_frozen_operating_coaching_v4_is_explicit_exception(self):
        prompt = load_prompt_template("coaching.md")
        self.assertNotIn("[역할]", prompt)
        self.assertIn("[출력 계약]", prompt)
        self.assertIn("[고정 Skill]", prompt)


if __name__ == "__main__":
    unittest.main()
