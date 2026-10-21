from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.question_rubric_generator import _to_feedback


RUBRIC = {
    "question_id": "preset-04",
    "question": "프로젝트 개발 중 발생한 문제를 어떻게 해결했나요?",
    "required_concepts": [
        {"id": "problem_context", "description": "문제 상황"},
        {"id": "own_action", "description": "본인의 해결 행동"},
        {"id": "result_verification", "description": "결과 확인"},
    ],
    "recommended_keywords": [],
}


class QuestionFeedbackContractTest(unittest.TestCase):
    def test_keeps_only_exact_answer_evidence_and_marks_missing_concepts(self) -> None:
        transcript = "로그인 오류를 확인했습니다. 입력값의 공백을 제거했습니다."
        payload = json.dumps({
            "covered_concepts": [
                {"id": "problem_context", "evidence": "로그인 오류를 확인했습니다."},
                {"id": "own_action", "evidence": "캐시를 재설계했습니다."},
            ],
            "contradictions": [],
            "feedback": "실제로 확인한 결과를 덧붙여 보세요.",
        }, ensure_ascii=False)

        result = _to_feedback(RUBRIC, payload, transcript)

        self.assertEqual(
            result["covered_concepts"],
            [{
                "id": "problem_context",
                "description": "문제 상황",
                "evidence": "로그인 오류를 확인했습니다.",
            }],
        )
        self.assertEqual(
            [item["id"] for item in result["missing_concepts"]],
            ["own_action", "result_verification"],
        )
        self.assertEqual(result["score"], 33)

    def test_contradiction_requires_two_distinct_exact_quotes(self) -> None:
        transcript = (
            "운영 계정에 쓰기 권한이 없음을 확인했습니다. "
            "같은 검사에서 쓰기 권한이 있음을 확인했습니다."
        )
        payload = json.dumps({
            "covered_concepts": [
                {"id": "result_verification", "evidence": "운영 계정에 쓰기 권한이 없음을 확인했습니다."},
            ],
            "contradictions": [{
                "id": "result_verification",
                "evidence": [
                    "운영 계정에 쓰기 권한이 없음을 확인했습니다.",
                    "같은 검사에서 쓰기 권한이 있음을 확인했습니다.",
                ],
                "reason": "같은 검사 결과의 권한 상태가 서로 다릅니다.",
            }],
            "feedback": "실제 권한 상태를 확인해 설명하세요.",
        }, ensure_ascii=False)

        result = _to_feedback(RUBRIC, payload, transcript)

        self.assertEqual(result["covered_concepts"], [])
        self.assertEqual(result["missing_concepts"][0]["id"], "problem_context")
        self.assertEqual(result["contradictions"][0]["id"], "result_verification")
        self.assertEqual(result["score"], 0)


if __name__ == "__main__":
    unittest.main()
