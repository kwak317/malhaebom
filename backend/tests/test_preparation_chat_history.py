import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.auth import create_require_authenticated_user
from app.core.supabase_settings import SupabaseSettings
from app.routers.preparation_conversation import register_preparation_routes
from app.services.preparation_conversation_repository import PreparationRepository
from app.services.supabase_persistence import SupabasePersistenceError
from tests.test_preparation_conversation_api import Verifier

class PreparationChatHistoryTest(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.state.coaching_service=SimpleNamespace(provider=None);app.state.coaching_observation_sink=None
        register_preparation_routes(app,create_require_authenticated_user(Verifier()))
        self.repository=SimpleNamespace(history=Mock(return_value=[{'role':'user','message':'Redis 경험을 추가할게요.','follow_up_question':None},{'role':'assistant','message':'반영할까요?','follow_up_question':None}]))
        app.state.preparation_conversation_service=SimpleNamespace(repository=self.repository)
        self.client=TestClient(app);self.sid=str(uuid4());self.path='/practice-records/'+self.sid+'/preparation-chat';self.headers={'Authorization':'Bearer test-token'}

    def test_authenticated_history_uses_current_owner(self):
        response=self.client.get(self.path,headers=self.headers);self.assertEqual(response.status_code,200)
        user,sid=self.repository.history.call_args.args;self.assertEqual(user.user_id,'owner');self.assertEqual(str(sid),self.sid)
        self.assertEqual([m['role'] for m in response.json()['messages']],['user','assistant'])

    def test_anonymous_denied(self):
        self.assertEqual(self.client.get(self.path).status_code,401);self.repository.history.assert_not_called()

    def test_missing_other_owner_expired_are_404(self):
        self.repository.history.side_effect=KeyError();self.assertEqual(self.client.get(self.path,headers=self.headers).status_code,404)

    def test_failure_is_not_empty_history(self):
        self.repository.history.side_effect=SupabasePersistenceError('FAILED','failed')
        self.assertEqual(self.client.get(self.path,headers=self.headers).status_code,503)

    def test_no_history_returns_empty(self):
        self.repository.history.return_value=[]
        self.assertEqual(self.client.get(self.path,headers=self.headers).json(),{'messages':[]})

    def test_repository_checks_session_then_filters_history(self):
        urls=[]
        def handle(request):
            urls.append(str(request.url))
            return httpx.Response(200,json=[{'state':{'history':[{'role':'user','text':'질문'}, {'role':'assistant','message':'답변','follow_up_question':'확인할까요?'}, {'role':'system','text':'hidden'}], 'sources':[{'text':'raw'}], 'responses':{'private':'not returned'}}}])
        settings=SupabaseSettings(url='https://db.example',publishable_key='public',service_role_key='server-test')
        repo=PreparationRepository(settings,httpx.Client(transport=httpx.MockTransport(handle)))
        repo.session=Mock(return_value={});user=SimpleNamespace(user_id='owner')
        messages=repo.history(user,self.sid);repo.session.assert_called_once_with(user,self.sid)
        self.assertIn('user_id=eq.owner',urls[0]);self.assertIn('practice_session_id=eq.'+self.sid,urls[0]);self.assertIn('expires_at=gt.',urls[0]);self.assertIn('order=created_at.asc',urls[0])
        self.assertEqual(len(messages),2);self.assertEqual(messages[0]['message'],'질문');self.assertEqual(messages[1]['follow_up_question'],'확인할까요?');self.assertNotIn('private',str(messages))

    def test_repository_never_queries_after_owner_check_fails(self):
        repo=PreparationRepository(SupabaseSettings(url='https://db.example',publishable_key='public',service_role_key='server-test'))
        repo.session=Mock(side_effect=KeyError());repo._request=Mock()
        with self.assertRaises(KeyError):repo.history(SimpleNamespace(user_id='owner'),self.sid)
        repo._request.assert_not_called()
