from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.coaching import (  # noqa: E402
    CoachingLLMOutput,
    CoachingStatus,
    ServerValidationContext,
    TerminalResponseReason,
)
from services.llm import (  # noqa: E402
    OutputContractError,
    build_terminal_response,
    validate_and_build_response,
)


def validation_context() -> ServerValidationContext:
    return ServerValidationContext.model_validate(
        {
            "requirement_ids": ["J01-R1"],
            "active_criterion_ids": [
                "problem_context",
                "cause_observation",
                "cause_inference",
                "own_action",
                "result_verification",
            ],
            "answer_segments": [
                {
                    "segment_id": "rev1-s1",
                    "text": "팀 프로젝트에서 로그인 오류가 발생했습니다.",
                },
                {
                    "segment_id": "rev1-s2",
                    "text": "저는 서버 로그를 확인하고 토큰 만료 처리 코드를 수정했습니다.",
                },
            ],
        }
    )


def valid_output() -> dict[str, object]:
    return {
        "job_alignment": [
            {
                "requirement_id": "J01-R1",
                "label": "related",
                "reason": "로그 확인과 오류 처리 코드 수정 경험이 관련됩니다.",
                "evidence": [
                    {
                        "segment_id": "rev1-s2",
                        "quote": "서버 로그를 확인하고 토큰 만료 처리 코드를 수정했습니다.",
                    }
                ],
            }
        ],
        "intent_assessment": {
            "label": "partial",
            "reason": "문제와 조치는 있지만 원인 판단과 결과 확인이 없습니다.",
        },
        "criterion_assessments": [
            {
                "criterion_id": "problem_context",
                "assessment": "met",
                "reason": "발생한 문제를 설명했습니다.",
                "evidence": [
                    {
                        "segment_id": "rev1-s1",
                        "quote": "로그인 오류가 발생했습니다.",
                    }
                ],
                "needed": None,
            },
            {
                "criterion_id": "cause_observation",
                "assessment": "not_observed",
                "reason": "관찰한 구체적 신호가 없습니다.",
                "evidence": [],
                "needed": "로그에서 실제로 관찰한 신호",
            },
            {
                "criterion_id": "cause_inference",
                "assessment": "not_observed",
                "reason": "관찰 신호로 원인을 좁힌 설명이 없습니다.",
                "evidence": [],
                "needed": "관찰 신호가 원인 후보를 가리킨 이유",
            },
            {
                "criterion_id": "own_action",
                "assessment": "met",
                "reason": "본인의 수정 행동을 설명했습니다.",
                "evidence": [
                    {
                        "segment_id": "rev1-s2",
                        "quote": "토큰 만료 처리 코드를 수정했습니다.",
                    }
                ],
                "needed": None,
            },
            {
                "criterion_id": "result_verification",
                "assessment": "not_observed",
                "reason": "수정 결과 확인이 없습니다.",
                "evidence": [],
                "needed": "수정 후 확인 방법과 관찰 결과",
            },
        ],
        "clarifying_question": "수정 후 오류 해결 여부를 어떻게 확인했나요?",
        "next_actions": [
            {
                "target_type": "criterion",
                "target_id": "cause_observation",
                "action": "로그에서 실제로 본 신호를 덧붙여 보세요.",
            },
            {
                "target_type": "criterion",
                "target_id": "result_verification",
                "action": "수정 뒤 확인 방법과 결과를 말해 보세요.",
            },
        ],
        "example_answer": (
            "팀 프로젝트에서 로그인 오류가 발생해 저는 서버 로그를 확인하고 "
            "토큰 만료 처리 코드를 수정했습니다. 이후 [실제로 확인한 방법과 결과]를 "
            "덧붙이겠습니다."
        ),
    }


class CoachingValidationTest(unittest.TestCase):
    def test_llm_schema_requires_evidence_for_openai_strict_json_schema(self):
        definitions = CoachingLLMOutput.model_json_schema()["$defs"]

        self.assertIn("evidence", definitions["JobAlignment"]["required"])
        self.assertIn("evidence", definitions["CriterionAssessment"]["required"])

    def test_valid_output_builds_server_fields(self):
        response = validate_and_build_response(valid_output(), validation_context())

        self.assertIs(response.status, CoachingStatus.NEEDS_MORE_INFO)
        self.assertEqual(
            set(response.model_dump(mode="json")),
            {
                "status",
                "job_alignment",
                "intent_assessment",
                "criterion_assessments",
                "evidence",
                "gaps",
                "clarifying_question",
                "next_actions",
                "example_answer",
            },
        )
        self.assertEqual(
            [gap.criterion_id for gap in response.gaps],
            ["cause_observation", "cause_inference", "result_verification"],
        )
        self.assertEqual(len(response.evidence), 3)

    def test_rejects_quote_not_present_in_answer(self):
        invalid = deepcopy(valid_output())
        invalid["criterion_assessments"][0]["evidence"][0]["quote"] = (
            "로그인 오류를 완전히 해결했습니다."
        )

        with self.assertRaises(OutputContractError) as raised:
            validate_and_build_response(invalid, validation_context())

        self.assertIn("정확히 존재하지 않습니다", str(raised.exception))

    def test_rejects_missing_and_duplicate_criterion_ids(self):
        invalid = deepcopy(valid_output())
        invalid["criterion_assessments"][4]["criterion_id"] = "own_action"

        with self.assertRaises(OutputContractError) as raised:
            validate_and_build_response(invalid, validation_context())

        message = str(raised.exception)
        self.assertIn("criterion_id 중복: own_action", message)
        self.assertIn("criterion_id 누락: result_verification", message)

    def test_rejects_unknown_action_target(self):
        invalid = deepcopy(valid_output())
        invalid["next_actions"][0]["target_id"] = "invented_criterion"

        with self.assertRaises(OutputContractError) as raised:
            validate_and_build_response(invalid, validation_context())

        self.assertIn("허용되지 않은 criterion target_id", str(raised.exception))

    def test_rejects_removed_cause_reasoning_id(self):
        invalid = deepcopy(valid_output())
        invalid["criterion_assessments"][1]["criterion_id"] = "cause_reasoning"

        with self.assertRaises(OutputContractError) as raised:
            validate_and_build_response(invalid, validation_context())

        self.assertIn("허용되지 않은 criterion_id", str(raised.exception))

    def test_rejects_english_explanation_and_placeholder_action(self):
        invalid = deepcopy(valid_output())
        invalid["intent_assessment"]["reason"] = "The answer matches the question."
        invalid["next_actions"][0]["action"] = "none"

        with self.assertRaises(OutputContractError) as raised:
            validate_and_build_response(invalid, validation_context())

        message = str(raised.exception)
        self.assertIn("intent_assessment.reason: 사용자 노출 문장은 한국어여야 합니다", message)
        self.assertIn("next_actions[0].action: 구체적인 연습 행동이 필요합니다", message)

    def test_rejects_met_without_evidence(self):
        invalid = deepcopy(valid_output())
        invalid["criterion_assessments"][0]["evidence"] = []

        with self.assertRaises(OutputContractError) as raised:
            validate_and_build_response(invalid, validation_context())

        self.assertIn(
            "met 판정에는 evidence가 1개 이상 필요합니다",
            str(raised.exception),
        )

    def test_builds_unavailable_response_without_llm_fields(self):
        response = build_terminal_response(
            TerminalResponseReason(
                status="unavailable",
                reason="코칭 결과를 검증하지 못했습니다.",
            )
        )

        self.assertIs(response.status, CoachingStatus.UNAVAILABLE)
        self.assertEqual(response.intent_assessment.label.value, "undetermined")
        self.assertEqual(response.job_alignment, [])
        self.assertEqual(response.next_actions, [])
        self.assertIsNone(response.example_answer)

    def test_rejects_example_answer_with_unconfirmed_number(self):
        invalid = deepcopy(valid_output())
        invalid["example_answer"] = "수정 후 오류가 30% 감소했다고 설명하겠습니다."

        with self.assertRaises(OutputContractError) as raised:
            validate_and_build_response(invalid, validation_context())

        self.assertIn("확정 답변에 없는 숫자 30", str(raised.exception))

    def test_rejects_missing_example_answer(self):
        invalid = deepcopy(valid_output())
        del invalid["example_answer"]

        with self.assertRaises(OutputContractError) as raised:
            validate_and_build_response(invalid, validation_context())

        self.assertIn("example_answer", str(raised.exception))

    def test_fully_supported_output_builds_ok_status(self):
        context = ServerValidationContext.model_validate(
            {
                "requirement_ids": ["J01-R1"],
                "active_criterion_ids": ["result_verification"],
                "answer_segments": [
                    {
                        "segment_id": "rev2-s1",
                        "text": "수정 후 같은 요청을 다시 보내 200 응답을 확인했습니다.",
                    }
                ],
            }
        )
        output = {
            "job_alignment": [
                {
                    "requirement_id": "J01-R1",
                    "label": "related",
                    "reason": "수정 결과를 직접 확인한 경험이 관련됩니다.",
                    "evidence": [
                        {
                            "segment_id": "rev2-s1",
                            "quote": "200 응답을 확인했습니다.",
                        }
                    ],
                }
            ],
            "intent_assessment": {
                "label": "aligned",
                "reason": "조치 후 확인 방법과 결과를 설명했습니다.",
            },
            "criterion_assessments": [
                {
                    "criterion_id": "result_verification",
                    "assessment": "met",
                    "reason": "동일 요청을 다시 보내 응답을 확인했습니다.",
                    "evidence": [
                        {
                            "segment_id": "rev2-s1",
                            "quote": "같은 요청을 다시 보내 200 응답을 확인했습니다.",
                        }
                    ],
                    "needed": None,
                }
            ],
            "clarifying_question": None,
            "next_actions": [
                {
                    "target_type": "criterion",
                    "target_id": "result_verification",
                    "action": "재현 조건도 함께 말하는 연습을 해 보세요.",
                }
            ],
            "example_answer": (
                "수정 후 같은 요청을 다시 보내 200 응답을 확인했습니다. "
                "이 확인 조건과 결과를 중심으로 설명하겠습니다."
            ),
        }

        response = validate_and_build_response(output, context)

        self.assertIs(response.status, CoachingStatus.OK)
        self.assertEqual(response.gaps, [])
        self.assertIsNone(response.clarifying_question)
        self.assertIn("200 응답", response.example_answer or "")


if __name__ == "__main__":
    unittest.main()
