from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import AuthenticatedUser
from app.services.practice_history import PracticeHistoryService


USER = AuthenticatedUser("user-1", "user-access-token")


def completed_row(
    job_id: str,
    session_id: str,
    attempt_no: int,
    completed_at: str,
    *,
    question_type: str = "preset",
    question_id: str | None = "preset-01",
    custom_question_text: str | None = None,
    text: str = "첫 답변",
    cpm: float = 330,
    long_silence_count: int = 2,
    repetition_count: int = 1,
    content_feedback: dict[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {"text": text, "internal": "never expose"}
    if content_feedback is not None:
        result["content_feedback"] = content_feedback
    return {
        "id": job_id,
        "user_id": "user-1",
        "practice_session_id": session_id,
        "question_type": question_type,
        "question_id": question_id,
        "custom_question_text": custom_question_text,
        "attempt_no": attempt_no,
        "audio_path": f"user-1/{job_id}/original.wav",
        "audio_content_type": "audio/wav",
        "completed_at": completed_at,
        "result": result,
        "delivery": {
            "metrics": {
                "cpm": cpm,
                "long_silences": [{} for _ in range(long_silence_count)],
                "repetitions": [{} for _ in range(repetition_count)],
            },
            "feedback": [
                {"code": "PACE", "evidence": "internal", "action": "속도를 조금 낮춰 보세요."},
                {"code": "SILENCE", "evidence": "internal", "action": "긴 멈춤을 줄여 보세요."},
                {"code": "EXTRA", "evidence": "internal", "action": "세 번째 피드백은 숨깁니다."},
            ],
        },
        "error": {"message": "internal"},
    }


class FakeRepository:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, str | None]] = []

    def list_completed_jobs(self, user: AuthenticatedUser) -> list[dict[str, object]]:
        self.calls.append(("list", user.user_id))
        return list(self.rows)

    def get_completed_session_jobs(self, user: AuthenticatedUser, practice_session_id: str) -> list[dict[str, object]]:
        self.calls.append(("completed-session", practice_session_id))
        rows = [row for row in self.rows if row["practice_session_id"] == practice_session_id]
        if not rows:
            raise KeyError(practice_session_id)
        return rows

    def get_session_jobs(self, user: AuthenticatedUser, practice_session_id: str) -> list[dict[str, object]]:
        self.calls.append(("all-session", practice_session_id))
        rows = [row for row in self.rows if row["practice_session_id"] == practice_session_id]
        if not rows:
            raise KeyError(practice_session_id)
        return rows

    def delete_session_jobs(self, user: AuthenticatedUser, practice_session_id: str, rows: list[dict[str, object]]) -> None:
        self.calls.append(("delete-session", practice_session_id))
        self.rows = [row for row in self.rows if row["practice_session_id"] != practice_session_id]


class PracticeHistoryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        rows = [
            completed_row("job-2", "session-a", 2, "2026-08-24T10:00:00+00:00", text="두 번째 답변", cpm=310, long_silence_count=1, repetition_count=0),
            completed_row("job-1", "session-a", 1, "2026-08-24T09:00:00+00:00"),
            completed_row("job-3", "session-b", 1, "2026-08-24T08:00:00+00:00", question_type="custom", question_id=None, custom_question_text="나의 협업 경험을 설명해 주세요.", text="협업 답변"),
        ]
        self.repository = FakeRepository(rows)
        self.service = PracticeHistoryService(self.repository)

    def test_list_groups_attempts_and_hides_private_storage_fields(self):
        result = self.service.list_records(USER)

        self.assertEqual([record["practice_session_id"] for record in result["records"]], ["session-a", "session-b"])
        first = result["records"][0]
        self.assertEqual(first["practiced_at"], "2026-08-24T10:00:00+00:00")
        self.assertEqual([attempt["attempt_no"] for attempt in first["attempts"]], [1, 2])
        self.assertEqual(first["attempts"][0], {
            "attempt_no": 1,
            "job_id": "job-1",
            "transcript": "첫 답변",
            "metrics": {"cpm": 330, "long_silence_count": 2, "repetition_count": 1},
            "feedback": ["속도를 조금 낮춰 보세요.", "긴 멈춤을 줄여 보세요."],
        })
        self.assertNotIn("audio_path", first["attempts"][0])
        self.assertNotIn("audio_content_type", first["attempts"][0])
        self.assertNotIn("user_id", first)
        self.assertNotIn("result", first["attempts"][0])
        self.assertNotIn("delivery", first["attempts"][0])
        self.assertNotIn("error", first["attempts"][0])

    def test_get_record_preserves_custom_question_and_attempt_order(self):
        record = self.service.get_record(USER, "session-b")

        self.assertEqual(record["question_type"], "custom")
        self.assertIsNone(record["question_id"])
        self.assertEqual(record["custom_question_text"], "나의 협업 경험을 설명해 주세요.")
        self.assertEqual([attempt["attempt_no"] for attempt in record["attempts"]], [1])

    def test_list_limits_to_fifty_sessions(self):
        rows = [
            completed_row(f"job-{index}", f"session-{index}", 1, f"2026-08-24T10:{index:02d}:00+00:00")
            for index in range(51)
        ]
        service = PracticeHistoryService(FakeRepository(rows))

        self.assertEqual(len(service.list_records(USER)["records"]), 50)

    def test_delete_record_checks_completed_rows_before_storage_delete(self):
        self.service.delete_record(USER, "session-a")

        self.assertEqual(self.repository.calls[-3:], [
            ("completed-session", "session-a"),
            ("all-session", "session-a"),
            ("delete-session", "session-a"),
        ])
        self.assertFalse(any(row["practice_session_id"] == "session-a" for row in self.repository.rows))

    def test_delete_all_records_only_deletes_current_users_completed_sessions(self):
        self.service.delete_all_records(USER)

        self.assertEqual(self.repository.calls, [
            ("list", "user-1"),
            ("completed-session", "session-a"),
            ("all-session", "session-a"),
            ("delete-session", "session-a"),
            ("completed-session", "session-b"),
            ("all-session", "session-b"),
            ("delete-session", "session-b"),
        ])
        self.assertEqual(self.repository.rows, [])

    def test_comparison_uses_same_criteria_and_keeps_evidence_with_its_attempt(self):
        rubric = {
            "required_concepts": [
                {"id": "problem_context", "description": "문제 상황"},
                {"id": "own_action", "description": "본인의 해결 행동"},
                {"id": "result_verification", "description": "결과 확인"},
            ]
        }
        first_feedback = {
            "rubric": rubric,
            "covered_concepts": [
                {"id": "problem_context", "evidence": "로그인 오류를 확인했습니다."},
                {"id": "own_action", "evidence": "공백을 제거했습니다."},
            ],
            "missing_concepts": [
                {"id": "result_verification", "description": "결과 확인"},
            ],
            "contradictions": [],
        }
        second_feedback = {
            "rubric": rubric,
            "covered_concepts": [
                {"id": "problem_context", "evidence": "로그인 오류를 재현했습니다."},
                {"id": "result_verification", "evidence": "두 입력 모두 로그인을 확인했습니다."},
            ],
            "missing_concepts": [],
            "contradictions": [{
                "id": "own_action",
                "reason": "공백 처리 여부가 서로 다릅니다.",
                "evidence": ["공백을 제거했습니다.", "공백을 제거하지 않았습니다."],
            }],
        }
        service = PracticeHistoryService(FakeRepository([
            completed_row(
                "job-2", "session-compare", 2, "2026-08-24T10:00:00+00:00",
                text="두 번째 답변", content_feedback=second_feedback,
            ),
            completed_row(
                "job-1", "session-compare", 1, "2026-08-24T09:00:00+00:00",
                text="첫 번째 답변", content_feedback=first_feedback,
            ),
        ]))

        comparison = service.get_record(USER, "session-compare")["comparison"]

        self.assertTrue(comparison["content_available"])
        self.assertEqual(
            comparison["added_explanations"],
            [{
                "criterion_id": "result_verification",
                "description": "결과 확인",
                "evidence": ["두 입력 모두 로그인을 확인했습니다."],
            }],
        )
        self.assertEqual(comparison["still_missing"][0]["criterion_id"], "own_action")
        self.assertEqual(comparison["contradictions"][0]["attempt_no"], 2)
        self.assertEqual(
            comparison["criteria"][0]["first"]["evidence"],
            ["로그인 오류를 확인했습니다."],
        )

    def test_content_comparison_is_unavailable_when_criteria_versions_differ(self):
        first_feedback = {
            "rubric": {"required_concepts": [{"id": "first", "description": "첫 기준"}]},
            "covered_concepts": [],
            "contradictions": [],
        }
        second_feedback = {
            "rubric": {"required_concepts": [{"id": "second", "description": "다른 기준"}]},
            "covered_concepts": [],
            "contradictions": [],
        }
        service = PracticeHistoryService(FakeRepository([
            completed_row("job-1", "session-mismatch", 1, "2026-08-24T09:00:00+00:00", content_feedback=first_feedback),
            completed_row("job-2", "session-mismatch", 2, "2026-08-24T10:00:00+00:00", content_feedback=second_feedback),
        ]))

        comparison = service.get_record(USER, "session-mismatch")["comparison"]

        self.assertFalse(comparison["content_available"])
        self.assertIn("기준이 달라", comparison["content_notice"])
        self.assertEqual(comparison["criteria"], [])

    def test_comparison_uses_confirmed_transcripts_and_saved_coaching_runs(self):
        def revision(text: str, assessments: list[dict[str, object]]) -> list[dict[str, object]]:
            return [{
                "confirmed_text": text,
                "confirmed_at": "2026-09-17T08:00:00+00:00",
                "delivery_metrics": {},
                "coaching_runs": [{
                    "created_at": "2026-09-17T08:01:00+00:00",
                    "response": {
                        "status": "needs_more_info",
                        "criterion_assessments": assessments,
                    },
                }],
            }]

        first = completed_row(
            "job-1", "session-coached", 1, "2026-09-17T08:00:00+00:00",
            text="수정 전 STT",
        )
        first["answer_revisions"] = revision("로그인 오류를 재현했습니다.", [{
            "criterion_id": "problem_context",
            "assessment": "partial",
            "reason": "문제는 있으나 발생 조건이 부족합니다.",
            "needed": "발생 조건",
            "evidence": [{"segment_id": "segment-1", "quote": "로그인 오류를 재현했습니다."}],
        }])
        second = completed_row(
            "job-2", "session-coached", 2, "2026-09-17T09:00:00+00:00",
            text="수정 전 2차 STT",
        )
        second["answer_revisions"] = revision(
            "공백 입력에서 로그인 오류를 재현했습니다.",
            [{
                "criterion_id": "problem_context",
                "assessment": "met",
                "reason": "발생 조건과 문제가 확인됩니다.",
                "needed": None,
                "evidence": [{"segment_id": "segment-2", "quote": "공백 입력에서 로그인 오류를 재현했습니다."}],
            }],
        )

        record = PracticeHistoryService(FakeRepository([second, first])).get_record(
            USER, "session-coached"
        )

        self.assertEqual(record["attempts"][0]["transcript"], "로그인 오류를 재현했습니다.")
        self.assertEqual(record["attempts"][1]["transcript"], "공백 입력에서 로그인 오류를 재현했습니다.")
        self.assertEqual(record["comparison"]["added_explanations"], [])
        self.assertEqual(record["comparison"]["criteria"][0]["change"], "changed")


if __name__ == "__main__":
    unittest.main()
