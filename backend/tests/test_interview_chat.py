from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.auth import AuthenticatedUser, InvalidAccessToken
from app.core.supabase_settings import SupabaseSettings
from app.main import create_app
from app.schemas.interview_chat import InterviewChatRequest
from app.services.coaching_errors import CoachingCreditsError, CoachingProviderError, CoachingRateLimitError, CoachingTimeoutError
from app.services.coaching_observability import NoopCoachingObservationSink
from app.services.coaching_questions import get_preset_coaching_question
from app.services.interview_chat import InterviewChatContextRepository, InterviewChatService, RECENT_MESSAGES
from app.services.practice_history import PracticeHistoryService
from services.llm import OutputContractError

SID = '90000000-0000-4000-8000-000000000001'
USER = AuthenticatedUser('owner', 'owner-token')


def fixture():
    now = datetime.now(UTC)
    expiry = (now + timedelta(hours=1)).isoformat()
    session = {'id': SID, 'user_id': 'owner', 'question_id': 'preset-04', 'expires_at': expiry,
        'job_postings': {'company': '개발용 가상 회사', 'title': '백엔드 개발', 'source_url': 'https://example.invalid/job', 'review_status': 'reviewed'},
        'practice_session_requirements': [{'job_requirements': {'code': 'R1', 'requirement_text': 'API 개발', 'source_excerpt': 'API 개발'}}]}
    rows = []
    for attempt in (1, 2):
        text = '로그인 오류가 발생했습니다. 로그를 확인하고 토큰 갱신 코드를 수정했습니다.'
        criteria = [{'criterion_id': cid, 'assessment': 'met' if cid in {'problem_context','own_action'} else 'not_observed',
            'reason': '개발용 판정', 'evidence': [{'segment_id': 's1', 'quote': text}] if cid in {'problem_context','own_action'} else [],
            'needed': None if cid in {'problem_context','own_action'} else '설명을 추가해 주세요.'}
            for cid in get_preset_coaching_question('preset-04').active_criterion_ids]
        rows.append({'id': f'job-{attempt}', 'user_id': 'owner', 'practice_session_id': SID,
            'attempt_no': attempt, 'question_type': 'preset', 'question_id': 'preset-04',
            'completed_at': now.isoformat(), 'expires_at': expiry, 'result': {'text': '수정 전 STT'},
            'delivery': {}, 'answer_revisions': [{'id': f'rev-{attempt}', 'confirmed_text': text,
                'confirmed_at': now.isoformat(), 'expires_at': expiry, 'delivery_metrics': {},
                'coaching_runs': [{'created_at': now.isoformat(), 'expires_at': expiry, 'skill_version': 'test-v1',
                    'model_name': 'test-only', 'prompt_version': 'test-prompt-v1',
                    'criteria_version': get_preset_coaching_question('preset-04').criteria_version,
                    'response': {'status': 'needs_more_info', 'criterion_assessments': criteria}}]}]})
    return session, rows


class Verifier:
    def verify_access_token(self, token):
        if token not in {'owner-token', 'other-token'}:
            raise InvalidAccessToken()
        return 'owner' if token == 'owner-token' else 'other'


class Provider:
    model_name = 'test-only'
    def __init__(self):
        self.inputs = []
        self.error = None
        self.invalid = 0
    def generate(self, *, system_prompt, user_prompt, schema):
        value, _ = json.JSONDecoder().raw_decode(user_prompt)
        self.inputs.append((system_prompt, value, schema))
        if self.error:
            raise self.error
        if self.invalid:
            self.invalid -= 1
            return {'message': 'invalid'}
        finish = value['action'] == 'finish'
        return {'message': '질문의 의도를 먼저 설명할게요.' if value['user_message'] and '?' in value['user_message'] else '함께 설명을 정리해 봐요.',
            'follow_up_question': None if finish else '수정 후 결과를 어떻게 확인했나요?',
            'memory': '사용자는 로그인 오류 경험을 설명했다. 결과 확인 방법을 물었다.',
            'summary': {'clarified_points': ['로그인 오류 경험을 정리했어요.'], 'next_practice': ['확인 조건을 설명해 보세요.']} if finish else None}


class InterviewChatTest(unittest.TestCase):
    def setUp(self):
        self.session, self.rows = fixture()
        self.requests = []
        self.save_status = 200
        self.before_save = None
        def transport(request):
            self.requests.append(request)
            owner = request.headers.get('Authorization') == 'Bearer owner-token'
            rows = [self.session] if request.url.path.endswith('practice_sessions') else self.rows
            job_filter = request.url.params.get('id')
            if request.url.path.endswith('analysis_jobs') and job_filter:
                rows = [row for row in rows if 'eq.' + row['id'] == job_filter]
            if request.method == 'PATCH':
                if self.before_save:
                    self.before_save()
                if self.save_status != 200:
                    return httpx.Response(self.save_status, json={'message': 'test-only storage unavailable'})
                if owner:
                    for row in rows:
                        row.update(json.loads(request.content))
            return httpx.Response(200, json=copy.deepcopy(rows) if owner else [])
        repository = InterviewChatContextRepository(SupabaseSettings('https://example.invalid', 'public-test-key'),
            httpx.Client(transport=httpx.MockTransport(transport)))
        self.provider = Provider()
        self.repository = repository
        self.service = InterviewChatService(repository, self.provider)
        self.client = TestClient(create_app(token_verifier=Verifier(), interview_chat_service=self.service,
            coaching_observation_sink=NoopCoachingObservationSink()))
        self.headers = {'Authorization': 'Bearer owner-token'}

    def post(self, action='start', conversation=None, message=None, token=None, **extra):
        body = {'action': action, 'request_id': str(uuid4()), 'practice_session_id': SID, **extra}
        if conversation: body['conversation_id'] = conversation
        if message is not None: body['message'] = message
        return self.client.post('/api/agent/chat', headers={'Authorization': 'Bearer ' + token} if token else self.headers, json=body)

    def start(self):
        response = self.post()
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['conversation_id']

    def test_server_context_start_message_finish_and_original_unchanged(self):
        original = copy.deepcopy(self.rows)
        cid = self.start()
        context = self.provider.inputs[0][1]['practice_context']
        self.assertIn('still_missing', context['comparison'])
        self.assertNotEqual(context['attempts'][0]['transcript'], '수정 전 STT')
        result = self.post('message', cid, '이 경험을 자기소개에 써도 될까요?')
        self.assertEqual(result.status_code, 200)
        self.assertIn('질문의 의도', result.json()['message'])
        result = self.post('finish', cid)
        self.assertEqual(result.json()['status'], 'finished')
        self.assertIsNone(result.json()['follow_up_question'])
        self.assertEqual(len(result.json()['summary']['next_practice']), 1)
        self.assertEqual(self.post('message', cid, '계속').status_code, 409)
        calls = len(self.provider.inputs)
        self.assertEqual(self.post('finish', cid).json(), result.json())
        self.assertEqual(len(self.provider.inputs), calls)
        archive = self.rows[1]['result'].pop('interview_chat')
        self.assertEqual(self.rows, original)
        self.assertEqual([entry['role'] for entry in archive['messages']], ['assistant', 'user', 'assistant', 'user', 'assistant'])
        self.assertEqual(archive['messages'][-2]['message'], '연습 마치기')
        patch = next(r for r in self.requests if r.method == 'PATCH')
        self.assertEqual(set(json.loads(patch.content)), {'result'})
        self.assertEqual(patch.url.params['user_id'], 'eq.owner')
        self.assertEqual(patch.url.params['attempt_no'], 'eq.2')
        self.assertEqual(patch.url.params['status'], 'eq.completed')
        self.assertTrue(patch.url.params['expires_at'].startswith('gt.'))
        self.assertTrue(all(r.headers['apikey'] == 'public-test-key' for r in self.requests))

    def test_start_is_idempotent(self):
        rid = str(uuid4())
        first = self.post(request_id=rid)
        second = self.post(request_id=rid)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(len(self.provider.inputs), 1)

    def test_new_start_and_lost_response_retry(self):
        cid = self.start()
        rid = str(uuid4())
        first = self.post('message', cid, '같은 조건으로 테스트했어요.', request_id=rid)
        second = self.post('message', cid, '같은 조건으로 테스트했어요.', request_id=rid)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(len(self.provider.inputs), 2)
        self.assertEqual(self.post('message', cid, '다른 답변', request_id=rid).status_code, 409)
        new_cid = self.start()
        self.assertNotEqual(new_cid, cid)
        self.assertEqual(self.post('message', cid, '오래된 대화').status_code, 404)

    def test_question_contract_rejects_two_question_fields(self):
        from app.schemas.interview_chat import InterviewChatOutput
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            InterviewChatOutput.model_validate({'message': '어떤 로그를 봤나요?', 'follow_up_question': '결과는 어떻게 확인했나요?', 'memory': '', 'summary': None})

    def test_missing_both_confirmed_coaching_results_blocks_model(self):
        for mutate in (lambda: self.rows.pop(), lambda: self.rows[1]['answer_revisions'].clear()):
            self.session, self.rows = fixture()
            mutate()
            self.assertEqual(self.post().status_code, 409)
        self.assertFalse(self.provider.inputs)

    def test_incompatible_question_criteria_and_skill_block_model(self):
        self.rows[1]['answer_revisions'][0]['coaching_runs'][0]['skill_version'] = 'different'
        self.assertEqual(self.post().status_code, 409)
        self.session, self.rows = fixture()
        self.rows[1]['question_id'] = 'preset-01'
        self.assertEqual(self.post().status_code, 404)
        self.assertFalse(self.provider.inputs)

    def test_auth_ownership_and_client_context_injection_rejected(self):
        self.assertEqual(self.client.post('/api/agent/chat', json={'action': 'start','practice_session_id': SID}).status_code, 401)
        self.assertEqual(self.post(token='other-token').status_code, 404)
        self.assertEqual(self.post(practice_context={'transcript': 'injected'}).status_code, 422)
        self.assertEqual(self.post(practice_session_id='bad-id').status_code, 422)
        self.assertFalse(self.provider.inputs)

    def test_expiry_and_deletion_revalidated_on_every_turn(self):
        cid = self.start()
        self.session['expires_at'] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        self.assertEqual(self.post('message', cid, '답변').status_code, 404)
        self.assertFalse(self.service.conversations)
        self.session, self.rows = fixture()
        cid = self.start()
        self.rows.clear()
        self.assertEqual(self.post('message', cid, '답변').status_code, 404)
        self.assertFalse(self.service.conversations)

    def test_long_conversation_has_bounded_context_not_turn_limit(self):
        cid = self.start()
        for index in range(20):
            self.assertEqual(self.post('message', cid, f'개발용 답변 {index}').status_code, 200)
        prompts = [item[1] for item in self.provider.inputs]
        self.assertTrue(all(len(item['recent_messages']) <= RECENT_MESSAGES for item in prompts))
        self.assertTrue(prompts[-1]['previous_conversation_summary'])

    def test_completed_full_history_survives_memory_clear_without_entering_model_context(self):
        cid = self.start()
        self.assertNotIn('interview_chat', self.rows[1]['result'])
        for index in range(20):
            self.assertEqual(self.post('message', cid, f'개발용 답변 {index}').status_code, 200)
        self.assertEqual(self.post('finish', cid).status_code, 200)
        self.service.conversations.clear()
        record = PracticeHistoryService(self.repository).get_record(USER, SID)
        history = record['interview_chat']
        self.assertEqual(len(history['messages']), 43)
        self.assertEqual(history['messages'][1]['message'], '개발용 답변 0')
        self.assertEqual(history['messages'][-3]['message'], '함께 설명을 정리해 봐요.')
        self.assertTrue(history['messages'][-1]['summary'])
        self.assertNotIn('fingerprint', history)
        self.assertNotIn('expires_at', history)
        self.start()
        self.assertNotIn('interview_chat', self.provider.inputs[-1][1]['practice_context'])

    def test_finish_storage_retry_reuses_generated_response_and_transcript(self):
        cid = self.start()
        rid = str(uuid4())
        self.save_status = 503
        failed = self.post('finish', cid, request_id=rid)
        self.assertEqual(failed.status_code, 503)
        self.assertIn('저장하거나', failed.json()['detail'])
        state = next(iter(self.service.conversations.values()))
        self.assertEqual(len(state.history_messages), 3)
        self.assertFalse(state.history_saved)
        self.assertNotIn('interview_chat', self.rows[1]['result'])
        self.save_status = 200
        retried = self.post('finish', cid, request_id=rid)
        self.assertEqual(retried.status_code, 200)
        self.assertEqual(len(self.provider.inputs), 2)
        self.assertEqual(len(state.history_messages), 3)
        self.assertTrue(state.history_saved)
        self.assertEqual(self.post('finish', cid, request_id=rid).json(), retried.json())
        self.assertEqual(sum(r.method == 'PATCH' for r in self.requests), 2)

    def test_standard_history_repository_fetches_archive_versions_for_list_and_detail(self):
        from app.services.supabase_persistence import SupabaseAnalysisRepository

        cid = self.start()
        self.assertEqual(self.post('finish', cid).status_code, 200)
        repository = SupabaseAnalysisRepository(self.repository.settings, self.repository.http)
        history = PracticeHistoryService(repository)
        self.assertIn('interview_chat', history.get_record(USER, SID))
        self.assertIn('interview_chat', history.list_records(USER)['records'][0])
        for request in self.requests[-2:]:
            selection = request.url.params['select']
            for name in ('model_name', 'prompt_version', 'skill_version', 'criteria_version'):
                self.assertIn(name, selection)

    def test_save_revalidates_changed_revision_expiry_and_deleted_record_after_generation(self):
        original_generate = self.provider.generate
        for change, status in (
            (lambda: self.rows[1]['answer_revisions'][0].update(id='changed-revision'), 409),
            (lambda: self.session.update(expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat()), 404),
            (lambda: self.rows.clear(), 404),
        ):
            self.session, self.rows = fixture()
            self.service.conversations.clear()
            self.provider.generate = original_generate
            cid = self.start()
            def generate(**kwargs):
                result = original_generate(**kwargs)
                change()
                return result
            self.provider.generate = generate
            self.assertEqual(self.post('finish', cid).status_code, status)
            self.assertFalse(any('interview_chat' in row['result'] for row in self.rows))
        self.assertFalse(any(r.method == 'PATCH' for r in self.requests))

    def test_job_polling_does_not_expose_unvalidated_archive_or_mutate_result(self):
        from app.services.persistent_analysis_jobs import _to_api_job
        row = self.rows[1]
        row['result']['interview_chat'] = {'messages': 'expired or invalid'}
        original = copy.deepcopy(row)
        job = _to_api_job(row)
        self.assertEqual(job['result'], {'text': '수정 전 STT'})
        self.assertEqual(row, original)

    def test_history_omits_expired_changed_or_corrupt_archive(self):
        cid = self.start()
        self.assertEqual(self.post('finish', cid).status_code, 200)
        original = copy.deepcopy(self.rows)
        for change in (
            lambda: self.rows[1]['result']['interview_chat'].update(expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(), completed_at=(datetime.now(UTC) - timedelta(hours=1)).isoformat()),
            lambda: self.rows[1]['answer_revisions'][0].update(id='changed-revision'),
            lambda: self.rows[1]['answer_revisions'][0]['coaching_runs'][0].update(prompt_version='changed-version'),
            lambda: self.rows[1]['result']['interview_chat'].update(fingerprint=['legacy'] * 4),
            lambda: self.rows[1]['result'].update(interview_chat={'messages': 'invalid'}),
        ):
            self.rows = copy.deepcopy(original)
            change()
            self.assertNotIn('interview_chat', PracticeHistoryService(self.repository).get_record(USER, SID))

    def test_failure_preserves_state_and_retry_does_not_duplicate(self):
        cid = self.start()
        state = next(iter(self.service.conversations.values()))
        before = copy.deepcopy(state.messages)
        for error, status in ((CoachingProviderError(),503), (CoachingTimeoutError(),504),
                              (CoachingRateLimitError(2),429), (CoachingCreditsError(),402)):
            self.provider.error = error
            self.assertEqual(self.post('message', cid, '확인했습니다.').status_code, status)
            self.assertEqual(state.messages, before)
        self.provider.error = None
        self.assertEqual(self.post('message', cid, '확인했습니다.').status_code, 200)
        self.assertEqual(sum(m['role'] == 'user' for m in state.messages), 1)

    def test_schema_repairs_once_then_502(self):
        self.provider.invalid = 1
        self.start()
        self.assertEqual(len(self.provider.inputs), 2)
        self.service.conversations.clear()
        self.provider.invalid = 2
        self.assertEqual(self.post().status_code, 502)
        self.assertFalse(next(iter(self.service.conversations.values())).messages)

    def test_wrong_conversation_and_changed_revision_are_blocked(self):
        cid = self.start()
        self.assertEqual(self.post('message', '90000000-0000-4000-8000-000000000999', '답변').status_code, 404)
        self.rows[1]['answer_revisions'][0]['id'] = 'changed-revision'
        self.assertEqual(self.post('message', cid, '답변').status_code, 409)
        self.assertEqual(len(self.provider.inputs), 1)

    def test_pending_turn_blocks_duplicate(self):
        cid = self.start()
        state = next(iter(self.service.conversations.values()))
        state.lock.acquire()
        try:
            self.assertEqual(self.post('message', cid, '답변').status_code, 409)
        finally:
            state.lock.release()
        self.assertEqual(len(self.provider.inputs), 1)


if __name__ == '__main__':
    unittest.main()
