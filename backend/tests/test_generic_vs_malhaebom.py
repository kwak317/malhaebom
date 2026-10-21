from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from evals.coaching_dataset import load_dataset  # noqa: E402
from evals.run_model_comparison import build_expected_output  # noqa: E402
from evals.generic_vs_malhaebom import (  # noqa: E402
    _live_case,
    _request,
    build_generic_user_prompt,
    render_markdown_report,
    resolve_case_ids,
)


class GenericVsMalhaebomTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = load_dataset(PROJECT_ROOT / "evals" / "dataset.v2.jsonl")[0]

    def test_generic_prompt_contains_only_question_and_answer(self):
        prompt = build_generic_user_prompt(self.case)

        self.assertEqual(set(prompt), {"question", "answer"})
        self.assertEqual(prompt["question"], self.case.question.text)
        self.assertEqual(
            prompt["answer"],
            "\n".join(segment.text for segment in self.case.context.answer_segments),
        )

    def test_explicit_case_ids_do_not_include_the_default_case(self):
        self.assertEqual(
            resolve_case_ids(["presentation-cause-01"]),
            ["presentation-cause-01"],
        )
        self.assertEqual(resolve_case_ids(None), ["coach-normal-01"])

    def test_markdown_shows_side_by_side_outputs_without_claiming_generic_score(self):
        markdown = render_markdown_report(
            {
                "model": "google/gemini-3.5-flash-lite",
                "mode": "mock",
                "cases": [
                    {
                        "case_id": self.case.id,
                        "question": self.case.question.text,
                        "answer": "\n".join(
                            segment.text for segment in self.case.context.answer_segments
                        ),
                        "generic": {"output": "범용 피드백", "failure": None},
                        "malhaebom": {
                            "output": {"criterion_assessments": []},
                            "failure": None,
                            "contract_valid": True,
                        },
                    }
                ],
            }
        )

        self.assertIn("# 범용 AI와 말해봄 비교", markdown)
        self.assertIn("## 범용 AI", markdown)
        self.assertIn("## 말해봄", markdown)
        self.assertIn("범용 피드백", markdown)
        self.assertIn("계약 검증: 통과", markdown)
        self.assertIn("범용 AI 응답은 정확도 점수로 환산하지 않습니다", markdown)

    def test_live_schema_failure_keeps_output_and_validation_field_paths(self):
        invalid_output = {"criterion_assessments": []}
        with patch(
            "evals.generic_vs_malhaebom._request",
            side_effect=[
                ("범용 피드백", {}, 1.0),
                (invalid_output, {}, 2.0),
                (invalid_output, {}, 3.0),
            ],
        ):
            result = _live_case(
                object(),
                self.case,
                model="test-model",
                system_prompt="test",
                max_completion_tokens=100,
            )

        malhaebom = result["malhaebom"]
        self.assertFalse(malhaebom["contract_valid"])
        self.assertEqual(malhaebom["output"], invalid_output)
        self.assertTrue(malhaebom["validation_error_fields"])

    def test_live_retries_one_contract_repair_before_recording_the_final_result(self):
        invalid_output = {"criterion_assessments": []}
        repaired_output = build_expected_output(self.case)
        with patch(
            "evals.generic_vs_malhaebom._request",
            side_effect=[
                ("범용 피드백", {}, 1.0),
                (invalid_output, {}, 2.0),
                (repaired_output, {}, 3.0),
            ],
        ):
            result = _live_case(
                object(),
                self.case,
                model="test-model",
                system_prompt="test",
                max_completion_tokens=100,
            )

        malhaebom = result["malhaebom"]
        self.assertTrue(malhaebom["contract_valid"])
        self.assertEqual(malhaebom["output"], repaired_output)
        self.assertTrue(malhaebom["repair_attempted"])

    def test_live_provider_failure_records_malhaebom_failure_without_stopping_case(self):
        with patch(
            "evals.generic_vs_malhaebom._request",
            side_effect=[
                ("범용 피드백", {}, 1.0),
                RuntimeError("provider unavailable"),
            ],
        ):
            result = _live_case(
                object(),
                self.case,
                model="test-model",
                system_prompt="test",
                max_completion_tokens=100,
            )

        self.assertEqual(result["generic"]["output"], "범용 피드백")
        self.assertIsNone(result["malhaebom"]["output"])
        self.assertEqual(result["malhaebom"]["failure"], "RuntimeError")
        self.assertFalse(result["malhaebom"]["contract_valid"])

    def test_structured_request_unwraps_a_json_object_encoded_as_a_string(self):
        expected = {"example_answer": "현재 답변의 사실만 재배열했습니다."}
        content = __import__("json").dumps(__import__("json").dumps(expected))
        completion = SimpleNamespace(
            model_dump=lambda mode: {
                "choices": [{"message": {"content": content}}],
                "usage": {},
            }
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: completion)
            )
        )

        output, _, _ = _request(
            client,
            model="test-model",
            system_prompt="test",
            user_payload={"question": "질문"},
            max_completion_tokens=128,
            response_format={"type": "json_schema"},
        )

        self.assertEqual(output, expected)

    def test_request_records_provider_finish_reason(self):
        completion = SimpleNamespace(
            model_dump=lambda mode: {
                "choices": [
                    {"finish_reason": "length", "message": {"content": "피드백"}}
                ],
                "usage": {},
            }
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: completion)
            )
        )

        _, usage, _ = _request(
            client,
            model="test-model",
            system_prompt="test",
            user_payload={"question": "질문"},
            max_completion_tokens=128,
            response_format=None,
        )

        self.assertEqual(usage.get("finish_reason"), "length")

if __name__ == "__main__":
    unittest.main()
