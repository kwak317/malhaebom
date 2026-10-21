from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.preparation_conversation_generation import generate_preparation_response
from app.services.preparation_conversation_policy import decide_preparation_action, PreparationPolicyError

VALID = {"intent": "answer", "message": "API는 시스템 사이의 인터페이스예요.", "follow_up_question": None, "next_action": "stay", "requested_stage": None, "profile_update": None}


def response(output=VALID, *, finish_reason="stop"):
    return {"choices": [{"finish_reason": finish_reason, "message": {"content": json.dumps(output, ensure_ascii=False)}}]}


class RecoveryTest(unittest.TestCase):
    def test_valid_response_calls_model_once(self):
        calls=[]
        def model():calls.append(1);return response()
        r=generate_preparation_response(model)
        self.assertEqual(len(calls), 1)
        self.assertFalse(r.recovered)
        self.assertEqual(r.output, VALID)

    def test_broken_json_retries_once_and_preserves_raw(self):
        raw={"choices":[{"finish_reason":"stop","message":{"content":"{broken"}}]}
        calls=[]
        def model():calls.append(1);return raw if len(calls)==1 else response()
        r=generate_preparation_response(model)
        self.assertTrue(r.recovered)
        self.assertEqual(r.attempts[0].provider_response, raw)
        self.assertEqual(r.attempts[0].error, "invalid_JSON")

    def test_length_limit_retries_even_if_fragment_looks_parseable(self):
        calls=[]
        def model():calls.append(1);return response(finish_reason="length" if len(calls)==1 else "stop")
        r=generate_preparation_response(model)
        self.assertEqual(r.attempts[0].error, "truncated_output")
        self.assertTrue(r.recovered)

    def test_invalid_schema_retries_once(self):
        calls=[]
        def model():calls.append(1);return response({"message":"부족한 필드"}) if len(calls)==1 else response()
        self.assertTrue(generate_preparation_response(model).recovered)

    def test_exhausted_recovery_leaves_context_unchanged(self):
        context={"pending_profile_update":{"draft_id":"d1","draft_version":2},"confirmed_supplemental_context":[]}
        before=copy.deepcopy(context);calls=[]
        def model():calls.append(copy.deepcopy(context));return response(finish_reason="length")
        r=generate_preparation_response(model)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(context, before)
        self.assertIsNone(r.output)
        self.assertIn("유지", r.failure_message)

    def test_transport_exception_is_not_retried_or_exposed(self):
        calls=[]
        def model():calls.append(1);raise TimeoutError("sensitive-provider-detail")
        r=generate_preparation_response(model)
        self.assertEqual(len(calls), 1)
        self.assertEqual(r.attempts[0].error, "TimeoutError")
        self.assertNotIn("sensitive", repr(r))

    def test_policy_error_is_not_repaired_into_save(self):
        bad={"intent":"profile_update","message":"동의를 확인했어요.","follow_up_question":None,"next_action":"stay","requested_stage":None,"profile_update":{"action":"request_save","draft_id":"invented","draft_version":1,"review_stage":None,"facts":[]}}
        r=generate_preparation_response(lambda:response(bad))
        self.assertEqual(len(r.attempts), 1)
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(r.output,{"current_stage":"resume","user_message":"고마워","available_actions":{},"pending_profile_update":None})


class FixedGuidanceTest(unittest.TestCase):
    def test_refusal_and_scope_guidance_remove_unnecessary_questions(self):
        for intent in ["refusal","out_of_scope"]:
            o=dict(VALID,intent=intent,message="궁금한 것을 알려주세요?",follow_up_question="무슨 일을 했나요?")
            d=decide_preparation_action(o,{"user_message":"일반 발화","current_stage":"resume"})
            self.assertEqual(d.response_source,"server_fixed")
            self.assertIsNone(d.follow_up_question)
            self.assertEqual(d.action,"stay")

    def test_simple_thanks_keeps_current_draft_and_input_unchanged(self):
        c={"user_message":"알겠어, 고마워.","current_stage":"resume","pending_profile_update":{"draft_id":"d1","status":"awaiting_confirmation"}}
        before=copy.deepcopy(c)
        o=dict(VALID,message="궁금하면 말씀해 주세요.")
        d=decide_preparation_action(o,c)
        self.assertEqual(d.message,"도움이 되었다니 다행이에요.")
        self.assertEqual(c,before)
        self.assertEqual(d.action,"stay")

    def test_thanks_plus_related_question_keeps_actual_answer(self):
        d=decide_preparation_action(VALID,{"user_message":"고마워. API가 정확히 뭐야?","current_stage":"ncs"})
        self.assertEqual(d.message,VALID["message"])
        self.assertEqual(d.response_source,"model")

    def test_guidance_does_not_override_malicious_action_fields(self):
        o=dict(VALID,intent="out_of_scope",next_action="request_rerecord")
        with self.assertRaises(PreparationPolicyError):
            decide_preparation_action(o,{"current_stage":"first_coaching","user_message":"저녁 메뉴 추천","available_actions":{"can_rerecord":True}})

    def test_optional_invitation_is_trimmed_without_losing_answer(self):
        o=dict(VALID,message="이미 저장된 동일 경력은 다시 반영하지 않아요. 새로운 경력이 있다면 알려주세요.")
        d=decide_preparation_action(o,{"current_stage":"resume","user_message":"같은 경력을 다시 반영해줘.","pending_profile_update":{"status":"saved"}})
        self.assertEqual(d.message,"이미 저장된 동일 경력은 다시 반영하지 않아요.")
        self.assertEqual(d.response_source,"server_trimmed_invitation")
        self.assertEqual(d.action,"stay")

    def test_real_information_question_is_not_trimmed(self):
        o=dict(VALID,message="어떤 직무인지 알려주세요.")
        with self.assertRaisesRegex(PreparationPolicyError,"question_in_message"):
            decide_preparation_action(o,{"current_stage":"resume","user_message":"어떤 정보가 필요해?"})


if __name__ == "__main__":
    unittest.main()
