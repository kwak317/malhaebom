from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for import_path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from evals.coaching_dataset import dataset_summary, load_dataset, score_response  # noqa: E402
from evals.run_model_comparison import (  # noqa: E402
    CandidateConfig,
    MockCandidateRunner,
    build_response_format,
    build_coaching_response_format,
    build_expected_output,
    reasoning_effort_for,
    run_comparison,
    select_cases,
)
from services.llm import validate_and_build_response  # noqa: E402


DATASET_PATH = PROJECT_ROOT / "evals" / "dataset.jsonl"


class CoachingEvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_dataset(DATASET_PATH)

    def test_dataset_has_30_balanced_documented_cases(self):
        self.assertEqual(len(self.cases), 30)
        self.assertEqual(
            dataset_summary(self.cases),
            {"normal": 12, "boundary": 10, "failure": 8},
        )
        for case in self.cases:
            self.assertTrue(case.why)
            self.assertIn("problem_context", case.context.active_criterion_ids)
            self.assertNotIn("situation", case.context.active_criterion_ids)
            if case.category == "failure":
                self.assertTrue(case.expected.failure_reason)

    def test_expected_fixture_passes_contract_and_scoring(self):
        for case in self.cases:
            with self.subTest(case=case.id):
                output = build_expected_output(case)
                response = validate_and_build_response(
                    output,
                    case.context,
                )
                self.assertEqual(score_response(case, response).accuracy, 1.0)
                self.assertEqual(output["example_answer"], response.example_answer)
                self.assertLessEqual(len(response.example_answer or ""), 500)

    def test_regression_evidence_uses_semantically_matching_segments(self):
        cases_by_id = {case.id: case for case in self.cases}
        expected_mappings = {
            ("coach-boundary-14", "job_alignment", "job-r1"): (
                "case-14-s1",
                "로그인 장애가 발생했고 팀에서 원인을 찾아 수정했습니다.",
            ),
            ("coach-boundary-15", "job_alignment", "job-r1"): (
                "case-15-s1",
                "응답이 느려서 제가 캐시를 적용했습니다.",
            ),
            ("coach-boundary-15", "criterion_assessment", "own_action"): (
                "case-15-s1",
                "응답이 느려서 제가 캐시를 적용했습니다.",
            ),
            ("coach-boundary-20", "criterion_assessment", "own_action"): (
                "case-20-s1",
                "다음에는 천천히 말했습니다.",
            ),
            ("coach-boundary-21", "job_alignment", "job-r1"): (
                "case-21-s1",
                "인증 오류를 발견해 제가 예외 처리를 추가했습니다.",
            ),
            ("coach-boundary-21", "criterion_assessment", "own_action"): (
                "case-21-s1",
                "인증 오류를 발견해 제가 예외 처리를 추가했습니다.",
            ),
        }

        for key, expected in expected_mappings.items():
            case_id, target_type, target_id = key
            with self.subTest(case=case_id, target=target_id):
                matching = [
                    evidence
                    for evidence in cases_by_id[case_id].expected.evidence
                    if evidence.target_type == target_type
                    and evidence.target_id == target_id
                ]
                self.assertEqual(len(matching), 1)
                self.assertEqual(
                    (matching[0].segment_id, matching[0].quote),
                    expected,
                )

    def test_runner_compares_contract_accuracy_cost_and_p95(self):
        expected = CandidateConfig("expected", "mock", "expected")
        degraded = CandidateConfig("degraded", "mock", "degraded")

        report = run_comparison(
            self.cases,
            [
                (expected, MockCandidateRunner("expected")),
                (degraded, MockCandidateRunner("degraded")),
            ],
        )

        expected_summary = report["candidates"]["expected"]
        degraded_summary = report["candidates"]["degraded"]
        self.assertEqual(expected_summary["contract_rate"], 1.0)
        self.assertEqual(expected_summary["accuracy"], 1.0)
        self.assertEqual(expected_summary["cost_usd"], 0.0)
        self.assertIn("p95_ms", expected_summary)
        self.assertLess(degraded_summary["contract_rate"], 1.0)
        self.assertLess(degraded_summary["accuracy"], 1.0)

    def test_ollama_candidate_uses_coaching_json_schema(self):
        candidate = CandidateConfig.parse("qwen=ollama:qwen3:4b")

        response_format = build_response_format(candidate)

        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(response_format["json_schema"]["name"], "coaching_output")
        self.assertIn("criterion_assessments", response_format["json_schema"]["schema"]["properties"])

    def test_openrouter_gemini_candidate_uses_strict_coaching_json_schema(self):
        candidate = CandidateConfig.parse(
            "gemini=openai:google/gemini-3.5-flash-lite"
        )

        response_format = build_response_format(candidate)

        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertIn(
            "criterion_assessments",
            response_format["json_schema"]["schema"]["properties"],
        )

    def test_openai_candidate_uses_strict_coaching_json_schema(self):
        candidate = CandidateConfig.parse("mini=openai:openai/gpt-5-mini")

        response_format = build_response_format(candidate)

        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertIn(
            "evidence",
            response_format["json_schema"]["schema"]["$defs"]["JobAlignment"][
                "required"
            ],
        )
        self.assertEqual(reasoning_effort_for(candidate), "minimal")

    def test_gpt6_candidate_uses_strict_coaching_json_schema(self):
        candidate = CandidateConfig.parse("sol=openai:openai/gpt-6-sol")

        response_format = build_response_format(candidate)

        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertIn(
            "evidence",
            response_format["json_schema"]["schema"]["$defs"]["JobAlignment"][
                "required"
            ],
        )

    def test_select_cases_returns_one_case_by_id(self):
        selected = select_cases(self.cases, ["coach-normal-01"])

        self.assertEqual([case.id for case in selected], ["coach-normal-01"])

    def test_select_cases_returns_multiple_cases_in_dataset_order(self):
        selected = select_cases(
            self.cases,
            ["coach-boundary-20", "coach-normal-04", "coach-normal-02"],
        )

        self.assertEqual(
            [case.id for case in selected],
            ["coach-normal-02", "coach-normal-04", "coach-boundary-20"],
        )

    def test_select_cases_rejects_unknown_case(self):
        with self.assertRaisesRegex(ValueError, "없는 case_id"):
            select_cases(self.cases, ["unknown-case"])

    def test_openai_compatible_runner_requests_strict_coaching_json_schema(self):
        response_format = build_coaching_response_format()

        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(response_format["json_schema"]["name"], "malhaebom_coaching")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(response_format["json_schema"]["schema"]["type"], "object")


if __name__ == "__main__":
    unittest.main()
