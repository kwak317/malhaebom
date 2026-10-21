from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.preparation_conversation_policy import (
    PreparationPolicyError, decide_preparation_action, preparation_completion_message,
)


def context():
    return {
        "current_stage": "resume", "user_message": "네, 요약한 경력이 맞아. 이번 연습에 반영해줘.",
        "source_messages": [{"message_id": "u1", "text": "A기업에서 2년간 근무했어."}],
        "available_actions": {"can_save_profile": True, "can_rerecord": False, "can_skip": False, "change_stage_targets": []},
        "pending_profile_update": {"draft_id": "d1", "draft_version": 2, "status": "awaiting_confirmation", "confirmation_requested": True},
        "confirmed_supplemental_context": [],
        "conversation_history": [{"role": "assistant", "message": "경력을 정리했어요.", "follow_up_question": "이 내용을 이번 연습에 반영할까요?"}],
    }


def output():
    return {"intent": "profile_update", "message": "저장 완료했습니다.", "follow_up_question": None,
            "next_action": "stay", "requested_stage": None,
            "profile_update": {"action": "request_save", "draft_id": "d1", "draft_version": 2, "review_stage": None, "facts": []}}


class PreparationPolicyTest(unittest.TestCase):
    def test_save_display_is_server_owned_and_failure_is_not_completion(self):
        c, o = context(), output()
        before = copy.deepcopy(c)
        d = decide_preparation_action(o, c)
        self.assertEqual(d.message, "정리한 내용에 대한 반영 동의를 확인했어요.")
        self.assertNotIn("저장했", preparation_completion_message(d, succeeded=False))
        self.assertIn("저장했", preparation_completion_message(d, succeeded=True))
        self.assertEqual(c, before)

    def test_save_requires_latest_draft(self):
        o = output(); o["profile_update"]["draft_version"] = 1
        with self.assertRaisesRegex(PreparationPolicyError, "latest_draft"):
            decide_preparation_action(o, context())

    def test_save_without_draft_is_rejected(self):
        c = context(); c["pending_profile_update"] = None
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(output(), c)

    def test_thanks_question_negation_and_new_facts_are_not_consent(self):
        for text in ["고마워", "알겠어", "반영해도 돼?", "네, 반영하지 마", "네, 요약은 맞아. 추가로 B기업에서 근무했어. 반영해줘"]:
            with self.subTest(text=text):
                c = context(); c["user_message"] = text
                with self.assertRaisesRegex(PreparationPolicyError, "save_consent_gate"):
                    decide_preparation_action(output(), c)

    def test_short_yes_only_after_current_summary_question(self):
        c = context(); c["user_message"] = "네"
        self.assertEqual(decide_preparation_action(output(), c).action, "request_save")
        c["conversation_history"][-1]["follow_up_question"] = "어떤 직무를 맡으셨나요?"
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(output(), c)

    def test_confirmation_can_refer_to_previously_added_experience(self):
        c = context()
        c["user_message"] = "네, 지금 추가로 설명한 경험의 요약이 맞아. 참고 정보로 반영해줘."
        self.assertEqual(decide_preparation_action(output(), c).action, "request_save")

    def test_no_save_while_collecting_pending_saved_or_disabled(self):
        for status in ["collecting", "save_pending", "saved"]:
            with self.subTest(status=status):
                c = context(); c["pending_profile_update"]["status"] = status
                with self.assertRaises(PreparationPolicyError):
                    decide_preparation_action(output(), c)
        c = context(); c["available_actions"]["can_save_profile"] = False
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(output(), c)

    def test_duplicate_version_not_saved(self):
        c = context(); c["confirmed_supplemental_context"] = [{"draft_id": "d1", "draft_version": 2}]
        with self.assertRaisesRegex(PreparationPolicyError, "duplicate_save"):
            decide_preparation_action(output(), c)

    def test_draft_confirmation_must_have_been_displayed(self):
        c = context(); c["pending_profile_update"]["confirmation_requested"] = False
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(output(), c)

    def test_proposal_source_cannot_be_invented(self):
        o = output(); o["message"] = "A기업에서 2년간 근무한 경력을 정리했어요."
        o["follow_up_question"] = "이 내용을 반영할까요?"
        o["profile_update"].update(action="propose", review_stage="awaiting_confirmation", facts=[{"kind": "company", "value": "A기업", "source_message_id": "u1", "source_excerpt": "B기업"}])
        with self.assertRaisesRegex(PreparationPolicyError, "invalid_source_quote"):
            decide_preparation_action(o, context())
        o["profile_update"]["facts"][0]["source_excerpt"] = "A기업"
        self.assertEqual(decide_preparation_action(o, context()).action, "propose")

    def test_question_only_in_separate_field(self):
        for message in ["반영할까요?", "어떤 직무인지 알려주세요."]:
            with self.subTest(message=message):
                o = output(); o["message"] = message
                with self.assertRaisesRegex(PreparationPolicyError, "question_in_message"):
                    decide_preparation_action(o, context())

    def test_discard_requires_user_request_and_only_unsaved_draft(self):
        o = output(); o["profile_update"]["action"] = "discard"
        c = context()
        with self.assertRaisesRegex(PreparationPolicyError, "discard_gate"):
            decide_preparation_action(o, c)
        c["user_message"] = "초안은 취소해줘."
        self.assertEqual(decide_preparation_action(o, c).action, "discard")
        c["pending_profile_update"]["status"] = "saved"
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(o, c)

    def test_rerecord_method_question_and_thanks_do_not_execute(self):
        o = {"intent": "change_step", "message": "녹음을 시작했어요.", "follow_up_question": None, "next_action": "request_rerecord", "requested_stage": None, "profile_update": None}
        c = context(); c["current_stage"] = "first_coaching"; c["available_actions"]["can_rerecord"] = True
        for text in ["다시 녹음하면 돼?", "고마워", "다시 녹음하지 마"]:
            c["user_message"] = text
            with self.subTest(text=text), self.assertRaises(PreparationPolicyError):
                decide_preparation_action(o, c)
        c["user_message"] = "이제 다시 녹음할게. 화면을 열어줘."
        d = decide_preparation_action(o, c)
        self.assertNotIn("시작했", d.message)
        c["current_stage"] = "resume"
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(o, c)

    def test_coaching_does_not_ask_for_progress(self):
        c = context(); c["current_stage"] = "first_coaching"
        o = {"intent": "answer", "message": "버튼으로 녹음할 수 있어요.", "follow_up_question": "바로 재녹음하시겠습니까?", "next_action": "stay", "requested_stage": None, "profile_update": None}
        with self.assertRaisesRegex(PreparationPolicyError, "unsolicited_coaching"):
            decide_preparation_action(o, c)

    def test_user_claim_does_not_prove_saved_state(self):
        c = context(); c["user_message"] = "방금 저장한 경력을 다시 반영해줘."
        o = {"intent": "answer", "message": "이미 저장 완료된 경력입니다.", "follow_up_question": None, "next_action": "stay", "requested_stage": None, "profile_update": None}
        with self.assertRaisesRegex(PreparationPolicyError, "unverified_save_completion"):
            decide_preparation_action(o, c)
        c["pending_profile_update"]["status"] = "saved"
        self.assertEqual(decide_preparation_action(o, c).action, "stay")

    def test_stage_enter_cannot_save_or_start_recording(self):
        c = context(); c["event"] = "stage_enter"
        with self.assertRaisesRegex(PreparationPolicyError, "stage_enter_gate"):
            decide_preparation_action(output(), c)

    def test_stage_and_skip_require_server_allowance_and_explicit_request(self):
        c = context(); c["user_message"] = "면접부터 하고 싶어."
        o = {"intent": "change_step", "message": "요청을 확인했어요.", "follow_up_question": None, "next_action": "request_change_stage", "requested_stage": "interview", "profile_update": None}
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(o, c)
        c["available_actions"]["change_stage_targets"] = ["interview"]
        self.assertEqual(decide_preparation_action(o, c).action, "request_change_stage")
        c["user_message"] = "API가 뭐야"
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(o, c)
        o.update(next_action="request_skip", requested_stage=None)
        c["user_message"] = "이 항목은 건너뛰고 싶어."
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(o, c)
        c["available_actions"]["can_skip"] = True
        self.assertEqual(decide_preparation_action(o, c).action, "request_skip")


if __name__ == "__main__":
    unittest.main()
