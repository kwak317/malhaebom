import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.supabase_persistence import SupabasePersistenceError
from tests.test_saramin_recommendation import FakeVerifierToken

class ConfirmedExperienceLibraryTest(unittest.TestCase):
    def client(self, repo):
        app = create_app(token_verifier=FakeVerifierToken())
        app.state.preparation_conversation_service = SimpleNamespace(repository=repo)
        return TestClient(app)

    def test_only_confirmed_facts_are_exposed_and_owner_is_scoped(self):
        repo = SimpleNamespace(load=Mock(return_value={'state': {
            'confirmed': [{'draft_id':'draft-1','facts':[{'kind':'role','value':'API 담당','source_excerpt':'API 담당'}]}],
            'pending': {'facts':[{'value':'초안'}]}}}))
        cid=uuid4()
        response=self.client(repo).get(f'/api/agent/preparation/{cid}/confirmed',headers={'Authorization':'Bearer owner-token'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['experiences'][0]['id'],'draft-1')
        self.assertTrue(response.json()['experiences'][0]['user_confirmed'])
        self.assertNotIn('초안',response.text)
        self.assertEqual(repo.load.call_args.args[0].user_id,'owner')
        self.assertEqual(repo.load.call_args.args[1],cid)

    def test_no_consent_returns_empty(self):
        repo=SimpleNamespace(load=Mock(return_value={'state':{'pending':{'facts':[{'value':'초안'}]}}}))
        response=self.client(repo).get(f'/api/agent/preparation/{uuid4()}/confirmed',headers={'Authorization':'Bearer owner-token'})
        self.assertEqual(response.json(),{'experiences':[]})

    def test_requires_auth(self):
        repo=SimpleNamespace(load=Mock())
        self.assertEqual(self.client(repo).get(f'/api/agent/preparation/{uuid4()}/confirmed').status_code,401)
        repo.load.assert_not_called()

    def test_missing_other_owner_or_expired_returns_404(self):
        repo=SimpleNamespace(load=Mock(side_effect=KeyError()))
        self.assertEqual(self.client(repo).get(f'/api/agent/preparation/{uuid4()}/confirmed',headers={'Authorization':'Bearer owner-token'}).status_code,404)

    def test_storage_failure_returns_503(self):
        repo=SimpleNamespace(load=Mock(side_effect=SupabasePersistenceError('unavailable','unavailable')))
        self.assertEqual(self.client(repo).get(f'/api/agent/preparation/{uuid4()}/confirmed',headers={'Authorization':'Bearer owner-token'}).status_code,503)
