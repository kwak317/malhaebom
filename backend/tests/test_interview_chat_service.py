"""HTTP 연결 전 서비스 상태와 main provider 결과 호환을 확인한다."""
import sys
import unittest
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.auth import AuthenticatedUser
from app.schemas.interview_chat import InterviewChatRequest
from app.services.coaching_runtime import CoachingProviderResult
import httpx
from app.core.supabase_settings import SupabaseSettings
from app.services.coaching_questions import get_preset_coaching_question
from app.services.interview_chat import InterviewChatConflict, InterviewChatContextRepository, InterviewChatService


ACTIVE = {'message': '확인 과정을 설명해 봐요.', 'follow_up_question': '어떤 조건에서 확인했나요?', 'memory': '', 'summary': None}


class InterviewChatContextTest(unittest.TestCase):
    def setUp(self):
        self.user = AuthenticatedUser('owner', 'test-token')
        self.sid = uuid4()
        self.question = get_preset_coaching_question('preset-01')
        expiry = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        self.session = {'user_id': self.user.user_id, 'question_id': self.question.question_id, 'expires_at': expiry,
            'job_postings': {'review_status': 'reviewed'}, 'practice_session_requirements': [{'job_requirements': {'code': 'req-1'}}]}
        self.rows = [{'id': str(uuid4()), 'user_id': self.user.user_id, 'practice_session_id': str(self.sid),
            'attempt_no': attempt, 'question_id': self.question.question_id, 'expires_at': expiry,
            'answer_revisions': [{'id': str(uuid4()), 'confirmed_text': '확인한 답변', 'confirmed_at': datetime.now(UTC).isoformat(),
                'expires_at': expiry, 'coaching_runs': [{'created_at': datetime.now(UTC).isoformat(), 'expires_at': expiry,
                    'model_name': 'model-1', 'prompt_version': 'prompt-1', 'skill_version': 'skill-1',
                    'criteria_version': self.question.criteria_version,
                    'response': {'status': 'ok', 'criterion_assessments': [{'criterion_id': cid,
                        'assessment': 'not_observed', 'reason': '추가 설명이 필요해요.', 'evidence': [], 'needed': '설명'}
                        for cid in self.question.active_criterion_ids]}}]}]} for attempt in (1, 2)]
        self.requests = []
        def respond(request):
            self.requests.append(request)
            return httpx.Response(200, json=[self.session] if request.url.path.endswith('practice_sessions') else self.rows)
        self.http = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(self.http.close)
        self.repository = InterviewChatContextRepository(SupabaseSettings('https://example.supabase.co', 'publishable'), self.http)
        self.provider = SimpleNamespace(generate=Mock(return_value=ACTIVE))

    def start(self):
        return InterviewChatService(self.repository, self.provider).respond(self.user,
            InterviewChatRequest(action='start', request_id=uuid4(), practice_session_id=self.sid))

    def test_matching_versions_start_and_query_retains_user_scope(self):
        self.start()
        self.provider.generate.assert_called_once()
        select = self.requests[1].url.params['select']
        for name in ('model_name', 'prompt_version', 'skill_version', 'criteria_version'):
            self.assertIn(name, select)
        self.assertTrue(all(request.headers['Authorization'] == 'Bearer test-token' for request in self.requests))

    def test_each_mismatched_version_blocks_generation(self):
        run = self.rows[1]['answer_revisions'][0]['coaching_runs'][0]
        for field in ('model_name', 'prompt_version', 'skill_version', 'criteria_version'):
            with self.subTest(field=field):
                original = run[field]
                run[field] = 'different-version'
                with self.assertRaises(InterviewChatConflict):
                    self.start()
                run[field] = original
        self.provider.generate.assert_not_called()

    def test_missing_blank_or_null_version_in_either_run_blocks_generation(self):
        for row in self.rows:
            run = row['answer_revisions'][0]['coaching_runs'][0]
            for field in ('model_name', 'prompt_version', 'skill_version', 'criteria_version'):
                original = run.pop(field)
                with self.subTest(attempt=row['attempt_no'], field=field, value='missing'):
                    with self.assertRaises(InterviewChatConflict):
                        self.start()
                for value in (None, ''):
                    run[field] = value
                    with self.subTest(attempt=row['attempt_no'], field=field, value=value):
                        with self.assertRaises(InterviewChatConflict):
                            self.start()
                run[field] = original
        self.provider.generate.assert_not_called()

    def test_both_old_criteria_versions_cannot_use_current_rules(self):
        for row in self.rows:
            row['answer_revisions'][0]['coaching_runs'][0]['criteria_version'] = 'old-criteria'
        with self.assertRaises(InterviewChatConflict):
            self.start()
        self.provider.generate.assert_not_called()


class InterviewChatReplayTest(unittest.TestCase):
    def setUp(self):
        self.provider = SimpleNamespace(generate=Mock(return_value=ACTIVE))
        repository = SimpleNamespace(
            load=Mock(return_value=({}, datetime.now(UTC) + timedelta(hours=1),
                ('revision-1', 'created-at', 'model-1', 'prompt-1', 'skill-1', 'criteria-1') * 2)),
            save_history=Mock(),
        )
        self.service = InterviewChatService(repository, self.provider)
        self.user = AuthenticatedUser('owner', 'test-token')
        self.sid = uuid4()
        self.start = InterviewChatRequest(action='start', request_id=uuid4(), practice_session_id=self.sid)
        self.first = self.service.respond(self.user, self.start)

    def request(self, action='message', message='확인했어요.', request_id=None):
        return InterviewChatRequest(action=action, request_id=request_id or uuid4(), practice_session_id=self.sid,
            conversation_id=self.first.conversation_id, message=message if action == 'message' else None)

    def test_replay_a_after_b_preserves_response_and_state(self):
        a = self.request(message='A 답변')
        self.provider.generate.return_value = {**ACTIVE, 'message': 'A 응답', 'memory': 'A 요약'}
        response_a = self.service.respond(self.user, a)
        self.provider.generate.return_value = {**ACTIVE, 'message': 'B 응답', 'memory': 'B 요약'}
        response_b = self.service.respond(self.user, self.request(message='B 답변'))
        state = self.service.conversations[(self.user.user_id, self.sid)]
        messages = deepcopy(state.messages)
        self.assertEqual(self.service.respond(self.user, a), response_a)
        self.assertEqual(state.messages, messages)
        self.assertEqual(state.memory, 'B 요약')
        self.assertEqual(state.last_response, response_b)
        self.assertEqual(self.provider.generate.call_count, 3)

    def test_older_id_rejects_changed_message_and_action(self):
        a = self.request()
        self.service.respond(self.user, a)
        self.service.respond(self.user, self.request(message='B 답변'))
        for request in (self.request(message='다른 A', request_id=a.request_id),
                        self.request(action='finish', request_id=a.request_id),
                        self.request(request_id=self.start.request_id),
                        InterviewChatRequest(action='start', request_id=a.request_id, practice_session_id=self.sid)):
            with self.subTest(action=request.action):
                with self.assertRaises(InterviewChatConflict):
                    self.service.respond(self.user, request)
        self.assertEqual(self.provider.generate.call_count, 3)

    def test_old_message_replay_after_finish_does_not_reopen_conversation(self):
        a = self.request()
        response_a = self.service.respond(self.user, a)
        self.provider.generate.return_value = {**ACTIVE, 'follow_up_question': None,
            'summary': {'clarified_points': [], 'next_practice': ['결과를 설명해 보세요.']}}
        self.service.respond(self.user, self.request(action='finish'))
        self.assertEqual(self.service.respond(self.user, a), response_a)
        with self.assertRaises(InterviewChatConflict):
            self.service.respond(self.user, self.request(message='새 답변'))
        self.assertEqual(self.provider.generate.call_count, 3)

    def test_failed_generation_can_retry_same_id(self):
        a = self.request()
        self.provider.generate.side_effect = [ValueError('실패'), ValueError('실패')]
        with self.assertRaises(ValueError):
            self.service.respond(self.user, a)
        self.provider.generate.side_effect = None
        response = self.service.respond(self.user, a)
        self.assertEqual(self.service.respond(self.user, a), response)
        self.assertEqual(self.provider.generate.call_count, 4)


class InterviewChatServiceTest(unittest.TestCase):
    def test_wrapped_provider_start_duplicate_finish_and_closed_state(self):
        active = {'message': '확인 과정을 설명해 봐요.', 'follow_up_question': '어떤 조건에서 확인했나요?', 'memory': '', 'summary': None}
        finished = {**active, 'follow_up_question': None, 'summary': {'clarified_points': [], 'next_practice': ['결과를 설명해 보세요.']}}
        provider = SimpleNamespace(generate=Mock(side_effect=[CoachingProviderResult(active), CoachingProviderResult(finished)]))
        repository = SimpleNamespace(
            load=Mock(return_value=({}, datetime.now(UTC) + timedelta(hours=1),
                ('revision-1', 'created-at', 'model-1', 'prompt-1', 'skill-1', 'criteria-1') * 2)),
            save_history=Mock(),
        )
        service = InterviewChatService(repository, provider)
        user = AuthenticatedUser('owner', 'test-token')
        sid = uuid4()
        start = InterviewChatRequest(action='start', request_id=uuid4(), practice_session_id=sid)
        first = service.respond(user, start)
        self.assertEqual(first, service.respond(user, start))
        self.assertEqual(provider.generate.call_count, 1)
        finish = InterviewChatRequest(action='finish', request_id=uuid4(), practice_session_id=sid, conversation_id=first.conversation_id)
        self.assertEqual(service.respond(user, finish).status, 'finished')
        self.assertEqual(provider.generate.call_count, 2)
        with self.assertRaises(InterviewChatConflict):
            service.respond(user, InterviewChatRequest(action='message', request_id=uuid4(), practice_session_id=sid, conversation_id=first.conversation_id, message='추가 질문'))
        self.assertEqual(provider.generate.call_count, 2)
