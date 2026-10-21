import json
import unittest
from copy import deepcopy
from unittest.mock import Mock
from uuid import uuid4

from app.core.auth import AuthenticatedUser
from app.routers.preparation_conversation import PreparationRequest
from app.services.preparation_conversation_policy import PreparationPolicyError
from app.services.preparation_conversation_repository import PreparationConflict, confirmed_context
from app.services.preparation_conversation_runtime import PreparationConversationService
from app.services.supabase_persistence import SupabasePersistenceError


def output(**changes):
    return dict(intent="answer", message="현재 내용을 설명했어요.", follow_up_question=None,
                next_action="stay", requested_stage=None, profile_update=None, **changes)


def provider(raw):
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(raw, ensure_ascii=False)}}]}


class MemoryRepository:
    def __init__(self):
        self.rows = {}
        self.fail = False

    def load(self, user, cid):
        row = self.rows.get(str(cid))
        if not row or row["user_id"] != user.user_id:
            raise KeyError(str(cid))
        return deepcopy(row)

    def create(self, user, cid):
        row = {"id": str(cid), "user_id": user.user_id, "state": {}, "version": 1, "practice_session_id": None}
        self.rows[str(cid)] = row
        return deepcopy(row)

    def save(self, user, row, state, session_id=None):
        if self.fail:
            raise SupabasePersistenceError("test", "failed")
        current = self.rows[row["id"]]
        if current["version"] != row["version"]:
            raise PreparationConflict("stale")
        current.update(state=deepcopy(state), version=row["version"]+1)
        if session_id:
            current["practice_session_id"] = str(session_id)

    def session(self, user, sid):
        if str(sid) != str(self.sid):
            raise KeyError(str(sid))
        return {}

    def first_coaching(self, user, sid):
        self.session(user, sid)
        return {"answer_revision_id": "actual-revision", "confirmed_answer": "원래 답변"}


class PreparationRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.repo.sid = uuid4()
        self.user = AuthenticatedUser("owner", "token")
        self.generate = Mock(return_value=provider(output()))
        self.service = PreparationConversationService(self.repo, self.generate, system_prompt="fixed")

    def request(self, message="설명해줘", **kwargs):
        return PreparationRequest(request_id=uuid4(), current_stage="resume", message=message, **kwargs)

    def propose(self, review_stage="awaiting_confirmation"):
        def generate(system, context):
            source = context["source_messages"][-1]
            return provider({**output(), "intent": "profile_update", "message": "A기업에서 일했어요.",
                "follow_up_question": "정리한 내용을 이번 연습에 반영할까요?",
                "profile_update": {"action": "propose", "draft_id": None, "draft_version": None,
                    "review_stage": review_stage, "facts": [{"kind": "company", "value": "A기업",
                        "source_message_id": source["message_id"], "source_excerpt": "A기업"}]}})
        self.generate.side_effect = generate
        return self.service.respond(self.user, self.request("A기업에 근무했어"))

    def save_output(self, cid):
        pending = self.repo.rows[cid]["state"]["pending"]
        self.generate.side_effect = None
        self.generate.return_value = provider({**output(), "intent": "profile_update", "profile_update": {
            "action": "request_save", "draft_id": pending["draft_id"], "draft_version": pending["draft_version"],
            "review_stage": None, "facts": []}})

    def test_displayed_save_question_prepares_confirmation_without_saving(self):
        response = self.propose(review_stage="collecting")
        cid = response["conversation_id"]
        self.assertIn("저장할까요?", response["follow_up_question"])
        self.assertIn("회사: A기업", response["message"])
        self.assertEqual(confirmed_context([self.repo.rows[cid]]), [])
        self.assertEqual(self.repo.rows[cid]["state"]["pending"]["status"], "awaiting_confirmation")
        self.assertFalse(self.generate.call_args.args[1]["available_actions"]["can_save_profile"])

    def test_displayed_summary_contains_every_actual_saved_fact_and_quote(self):
        response = self.propose()
        self.assertIn("회사: A기업", response["message"])
        self.assertEqual(self.repo.rows[response["conversation_id"]]["state"]["pending"]["facts"][0]["source_excerpt"], "A기업")
        self.assertIn(self.repo.rows[response["conversation_id"]]["state"]["pending"]["summary"], response["message"])

    def test_explicit_consent_saves_only_server_pending_then_replay_is_idempotent(self):
        cid = self.propose()["conversation_id"]
        self.save_output(cid)
        request = self.request("맞아, 반영해줘", conversation_id=cid)
        result = self.service.respond(self.user, request)
        self.assertIn("저장했어요", result["message"])
        calls = self.generate.call_count
        self.assertEqual(self.service.respond(self.user, request), result)
        self.assertEqual(self.generate.call_count, calls)
        confirmed = confirmed_context([self.repo.rows[cid]])
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(confirmed[0]["usage"], "reference_only")

    def test_ambiguous_consent_does_not_save(self):
        cid = self.propose()["conversation_id"]
        self.save_output(cid)
        response = self.service.respond(self.user, self.request("괜찮을까?", conversation_id=cid))
        self.assertEqual(response["status"], "unavailable")
        self.assertIsNone(response["follow_up_question"])
        self.assertIn("반영하려면", response["message"])
        self.assertNotIn("confirmed", self.repo.rows[cid]["state"])

    def test_save_failure_has_no_completion_or_mutation(self):
        cid = self.propose()["conversation_id"]
        self.save_output(cid)
        before = deepcopy(self.repo.rows[cid])
        self.repo.fail = True
        request = self.request("어 반영해줘", conversation_id=cid)
        response = self.service.respond(self.user, request)
        self.assertEqual(response["status"], "unavailable")
        self.assertNotIn("저장했어요", response["message"])
        self.assertIsNone(response["follow_up_question"])
        self.assertIn("반영하려면", response["message"])
        self.assertEqual(self.repo.rows[cid], before)
        self.repo.fail = False
        result = self.service.respond(self.user, request)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(self.repo.rows[cid]["state"]["confirmed"]), 1)
        before = deepcopy(self.repo.rows[cid])
        self.assertEqual(self.repo.rows[cid], before)

    def test_first_coaching_context_is_server_loaded_and_does_not_edit_answer(self):
        request = PreparationRequest(request_id=uuid4(), current_stage="first_coaching", message="왜 이렇게 평가했어?",
            practice_session_id=self.repo.sid)
        self.service.respond(self.user, request)
        context = self.generate.call_args.args[1]
        self.assertEqual(context["coaching_context"]["answer_revision_id"], "actual-revision")
        self.assertEqual(context["coaching_context"]["confirmed_answer"], "원래 답변")

    def test_wrong_owner_does_not_generate(self):
        cid = self.propose()["conversation_id"]
        calls = self.generate.call_count
        with self.assertRaises(KeyError):
            self.service.respond(AuthenticatedUser("other", "token"), self.request(conversation_id=cid))
        self.assertEqual(self.generate.call_count, calls)

    def test_cannot_rebind_to_another_session(self):
        cid = self.propose()["conversation_id"]
        self.service.bind(self.user, cid, self.repo.sid)
        other = uuid4()
        self.repo.sid = other
        with self.assertRaises(PreparationConflict):
            self.service.bind(self.user, cid, other)

    def test_two_invalid_generations_leave_state_unchanged(self):
        self.generate.return_value = {"choices": [{"message": {"content": "invalid"}}]}
        request = self.request()
        result = self.service.respond(self.user, request)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(self.generate.call_count, 2)
        self.assertEqual(self.repo.rows[str(request.request_id)]["state"], {})

    def test_rerecord_is_request_and_no_premature_opened_claim(self):
        self.generate.return_value = provider({**output(), "intent": "change_step", "next_action": "request_rerecord"})
        result = self.service.respond(self.user, PreparationRequest(request_id=uuid4(), current_stage="first_coaching",
            message="이제 다시 녹음할게", practice_session_id=self.repo.sid))
        self.assertEqual(result["action"], "request_rerecord")
        self.assertNotIn("열었", result["message"])

    def test_concurrent_version_change_does_not_overwrite(self):
        cid = self.propose()["conversation_id"]
        self.save_output(cid)
        original_save = self.repo.save
        def change_version(user, row, state, session_id=None):
            self.repo.rows[cid]["version"] += 1
            return original_save(user, row, state, session_id)
        self.repo.save = change_version
        response = self.service.respond(self.user, self.request("맞아, 반영해줘", conversation_id=cid))
        self.assertEqual(response["status"], "unavailable")
        self.assertIn("최신 정리", response["message"])
        self.assertIsNone(response["follow_up_question"])
        self.assertIn("반영하려면", response["message"])
        self.assertNotIn("confirmed", self.repo.rows[cid]["state"])

    def test_natural_consent_does_not_call_model(self):
        for message in ("어 반영해줘", "응 저장해줘", "네, 반영해주세요", "좋아요 그대로 반영해 주세요", "정리한 내용이 맞아요. 이번 연습에 반영해 주세요."):
            with self.subTest(message=message):
                cid = self.propose()["conversation_id"]
                calls = self.generate.call_count
                self.generate.side_effect = RuntimeError("provider unavailable")
                response = self.service.respond(self.user, self.request(message, conversation_id=cid))
                self.assertEqual(response["status"], "ok")
                self.assertEqual(self.generate.call_count, calls)
                self.assertEqual(len(self.repo.rows[cid]["state"]["confirmed"]), 1)

    def test_invalid_model_response_reasks_consent_without_mutating_draft(self):
        cid = self.propose()["conversation_id"]
        before = deepcopy(self.repo.rows[cid])
        self.generate.side_effect = None
        self.generate.return_value = {"choices": [{"message": {"content": "invalid"}}]}
        response = self.service.respond(self.user, self.request("알겠어", conversation_id=cid))
        self.assertIsNone(response["follow_up_question"])
        self.assertIn("반영하려면", response["message"])
        self.assertIn(before["state"]["pending"]["summary"], response["message"])
        self.assertEqual(self.repo.rows[cid], before)
        self.generate.side_effect = RuntimeError("not called")
        result = self.service.respond(self.user, self.request("어 반영해줘", conversation_id=cid))
        self.assertEqual(result["status"], "ok")

    def test_save_response_loss_retry_checks_already_saved_state(self):
        cid = self.propose()["conversation_id"]
        original_save = self.repo.save
        def save_then_lose_response(user, row, state, session_id=None):
            original_save(user, row, state, session_id)
            raise SupabasePersistenceError("test", "response lost")
        self.repo.save = save_then_lose_response
        response = self.service.respond(self.user, self.request("어 반영해줘", conversation_id=cid))
        self.assertEqual(response["status"], "unavailable")
        version = self.repo.rows[cid]["version"]
        self.generate.side_effect = RuntimeError("must not call model")
        result = self.service.respond(self.user, self.request("응 저장해줘", conversation_id=cid))
        self.assertEqual(result["status"], "ok")
        self.assertIn("이미", result["message"])
        self.assertEqual(self.repo.rows[cid]["version"], version)
        self.assertEqual(len(self.repo.rows[cid]["state"]["confirmed"]), 1)

    def test_free_question_preserves_followup_and_history(self):
        self.generate.return_value = provider({**output(), "message": "선택한 역량은 백엔드 API 개발 경험과 연결해 설명하기 좋아요.",
            "follow_up_question": "서버 구현 경험이 있으신가요?"})
        response = self.service.respond(self.user, self.request("선택한 NCS 역량을 어떻게 설명할까?"))
        self.assertEqual(response["message"], "선택한 역량은 백엔드 API 개발 경험과 연결해 설명하기 좋아요.")
        self.assertEqual(response["follow_up_question"], "서버 구현 경험이 있으신가요?")
        self.assertEqual(self.repo.rows[response["conversation_id"]]["state"]["history"][-1]["follow_up_question"], response["follow_up_question"])

    def test_experience_proposal_uses_statement_and_short_consent_still_saves(self):
        response = self.propose()
        self.assertEqual(response["follow_up_question"], "이 내용을 연습 참고정보로 저장할까요?")
        self.assertNotIn("?", response["message"])
        self.assertIn("연습 참고정보 후보", response["message"])
        result = self.service.respond(self.user, self.request("네", conversation_id=response["conversation_id"]))
        self.assertEqual(result["status"], "ok")
        self.assertIn("저장했어요", result["message"])

    def test_question_in_message_is_rejected_by_contract(self):
        self.generate.return_value = provider({**output(), "message": "API 개발은 역할과 확인한 결과를 설명하면 좋아요. 어떤 API를 개발했나요?",
            "follow_up_question": "맡은 역할은 무엇인가요? 결과도 알려주시겠어요?"})
        with self.assertRaises(PreparationPolicyError):
            self.service.respond(self.user, self.request("API 경험을 어떻게 설명할까?"))

    def test_clarification_preserves_question_without_save(self):
        self.generate.return_value = provider({**output(), "intent": "clarify", "message": "현재 자료로는 구체적인 경험을 확인하기 어려워요.",
            "follow_up_question": "경험을 알려주실래요?"})
        request = self.request("어떤 경험을 먼저 설명할까?")
        result = self.service.respond(self.user, request)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["follow_up_question"], "경험을 알려주실래요?")
        self.assertNotIn("confirmed", self.repo.rows[str(request.request_id)]["state"])


    def test_cached_response_checks_session_expiry_before_returning(self):
        request = self.request(practice_session_id=self.repo.sid)
        self.service.respond(self.user, request)
        calls = self.generate.call_count
        self.repo.session = Mock(side_effect=KeyError("expired"))
        with self.assertRaises(KeyError):
            self.service.respond(self.user, request)
        self.repo.session.assert_called_once()
        self.assertEqual(self.generate.call_count, calls)

    def test_cached_first_coaching_checks_current_stage_before_returning(self):
        request = PreparationRequest(request_id=uuid4(), current_stage="first_coaching",
            message="설명해줘", practice_session_id=self.repo.sid)
        self.service.respond(self.user, request)
        calls = self.generate.call_count
        self.repo.first_coaching = Mock(side_effect=PreparationConflict("second answer completed"))
        with self.assertRaises(PreparationConflict):
            self.service.respond(self.user, request)
        self.repo.first_coaching.assert_called_once()
        self.assertEqual(self.generate.call_count, calls)


class PreparationPromptLoadingTest(unittest.TestCase):
    def test_nested_json_braces_are_preserved_and_skill_is_inserted_once(self):
        from unittest.mock import patch
        from app.services.preparation_conversation_runtime import load_preparation_prompt
        source = '## System 본문\n{{prompt_version}} {{skill_version}} {{skill_text}} {"nested":{"value":1}}\n## 계약 예시'
        with patch("pathlib.Path.read_text", side_effect=[source, "---\nname: fixture\n---\n규칙 {{literal}}"]):
            rendered = load_preparation_prompt()
        self.assertIn('{"nested":{"value":1}}', rendered)
        self.assertIn('규칙 {{literal}}', rendered)
        self.assertNotIn('{{skill_text}}', rendered)

    def test_unknown_prompt_slot_is_rejected(self):
        from unittest.mock import patch
        from app.services.preparation_conversation_runtime import load_preparation_prompt
        from app.services.prompt_templates import PromptTemplateError
        source = '## System 본문\n{{prompt_version}} {{skill_version}} {{skill_text}} {{unknown}}\n## 계약 예시'
        with patch("pathlib.Path.read_text", side_effect=[source, "---\nname: fixture\n---\n규칙"]):
            with self.assertRaises(PromptTemplateError):
                load_preparation_prompt()
