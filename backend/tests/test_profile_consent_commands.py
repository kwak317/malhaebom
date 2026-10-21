import unittest
from app.services.preparation_conversation_policy import explicit_profile_consent
class ConsentCommandTests(unittest.TestCase):
    def test_variants_and_rejections(self):
        pending={"status":"awaiting_confirmation","confirmation_requested":True}
        for message in ["반영", "반영하기", "반영해주세요", "응 반영하기", "정리한 내용을 반영하기", "반영해줘"]:
            self.assertTrue(explicit_profile_consent({"pending_profile_update":pending,"user_message":message}),message)
        for message in ["반영하지 마", "반영하기 전에 질문 있어요", "반영하면 어떻게 돼요?", "수정하고 반영해줘", "다른 경력도 반영해줘", "반영 취소"]:
            self.assertFalse(explicit_profile_consent({"pending_profile_update":pending,"user_message":message}),message)
        self.assertFalse(explicit_profile_consent({"user_message":"반영하기"}))
