import unittest
from uuid import uuid4

from app.core.auth import AuthenticatedUser
from app.routers.preparation_conversation import PreparationRequest
from app.services.free_chat import claims_unverified_execution
from app.services.preparation_restart import restart_guidance
from app.services.preparation_conversation_runtime import PreparationConversationService
from test_preparation_conversation_runtime import MemoryRepository, output, provider


class ProductionChatSyncTest(unittest.TestCase):
    def test_personal_work_confirmation_then_separate_save_consent(self):
        repo = MemoryRepository()
        repo.sid = uuid4()
        user = AuthenticatedUser("owner", "token")
        calls = []
        statement = "팀 프로젝트에서 Redis 캐시 적용 전후의 응답 시간을 비교했습니다."

        def generate(prompt, context):
            calls.append(context)
            if len(calls) == 1:
                return provider({**output(), "follow_up_question": "본인이 직접 수행한 작업인가요?"})
            source = context["source_messages"][0]
            return provider({**output(), "intent": "profile_update",
                "follow_up_question": "이 경험을 연습 참고정보로 저장할까요?",
                "profile_update": {"action": "propose", "draft_id": None, "draft_version": None,
                    "review_stage": "awaiting_confirmation", "facts": [{"kind": "role",
                        "value": statement, "source_message_id": source["message_id"],
                        "source_excerpt": statement}]}})

        service = PreparationConversationService(repo, generate, system_prompt="test")
        first = service.respond(user, PreparationRequest(request_id=uuid4(), current_stage="ncs", message=statement))
        cid = first["conversation_id"]
        confirmed_work = service.respond(user, PreparationRequest(request_id=uuid4(), conversation_id=cid,
            current_stage="ncs", message="네 맞습니다"))
        self.assertIn("저장할까요?", confirmed_work["follow_up_question"])
        self.assertFalse(repo.rows[cid]["state"].get("confirmed"))
        saved = service.respond(user, PreparationRequest(request_id=uuid4(), conversation_id=cid,
            current_stage="ncs", message="네"))
        self.assertIn("저장했어요", saved["message"])
        self.assertEqual(len(repo.rows[cid]["state"]["confirmed"]), 1)
        self.assertEqual(repo.rows[cid]["state"]["confirmed"][0]["usage"], "reference_only")
        self.assertEqual(len(calls), 2)

    def test_future_job_stage_is_blocked_and_completed_stage_is_allowed(self):
        self.assertIn("아직", restart_guidance("jobs", PreparationRequest(request_id=uuid4(), current_stage="ncs", message="공고 다시 선택")))
        self.assertIn("현재", restart_guidance("jobs", PreparationRequest(request_id=uuid4(), current_stage="readme", ui_context="jobs", message="공고 다시 선택")))
        self.assertIsNone(restart_guidance("jobs", PreparationRequest(request_id=uuid4(), current_stage="readme", ui_context="questions", message="공고 다시 선택")))

    def test_fake_completion_cannot_hide_inside_emphasis(self):
        self.assertTrue(claims_unverified_execution("**이력서에 추가 정보를 저장했어요.**"))
        self.assertFalse(claims_unverified_execution("추가할 문장을 먼저 정리해 드릴게요."))


if __name__ == "__main__":
    unittest.main()
