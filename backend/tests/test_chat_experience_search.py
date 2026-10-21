import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas.saramin_recommendation import SaraminRecommendationRequest, SaraminRecommendationResponse
from app.services.saramin_recommendation import SaraminRecommendationService
from app.services.supabase_persistence import SupabasePersistenceError
from tests.test_saramin_recommendation import FakeVerifierToken, FakeSearch, FakeVerifier

class ChatExperienceSearchTest(unittest.TestCase):
    def setUp(self):
        self.search = FakeSearch()
        self.service = SaraminRecommendationService(self.search, FakeVerifier())
        self.request = SaraminRecommendationRequest(selected_ncs_ids=['skill-server'])
        self.confirmed = [{'source_type':'user_chat','user_confirmed':True,'facts':[
            {'kind':'technology','value':'Spring Boot'},
            {'kind':'responsibility','value':'API 구현을 담당했습니다.'}]}]

    def test_confirmed_chat_is_used_for_search_and_reason(self):
        jobs = self.service.recommend(self.request, confirmed_experience=self.confirmed).recommendations
        self.assertIn('Spring Boot', self.search.technologies)
        self.assertIn('API', self.search.technologies)
        self.assertEqual(jobs[0].matched_chat_experience, ['Spring Boot', 'API'])
        self.assertEqual(jobs[0].matched_resume_technologies, [])

    def test_unconfirmed_and_document_facts_are_excluded(self):
        for item in [dict(self.confirmed[0],user_confirmed=False),dict(self.confirmed[0],source_type='resume')]:
            self.service.recommend(self.request,confirmed_experience=[item])
            self.assertEqual(self.search.technologies, [])

    def client(self, repository):
        service=SimpleNamespace(recommend=Mock(return_value=SaraminRecommendationResponse(recommendations=[],searched_at='now')))
        app=create_app(token_verifier=FakeVerifierToken(),saramin_recommendation_service=service)
        app.state.preparation_conversation_service=SimpleNamespace(repository=repository)
        return TestClient(app),service

    def test_owner_scoped_repository_supplies_only_confirmed(self):
        cid=str(uuid4());repo=SimpleNamespace(load=Mock(return_value={'state':{'confirmed':self.confirmed,'pending':{'facts':[{'kind':'technology','value':'Redis'}]}}}))
        client,service=self.client(repo)
        response=client.post('/api/job-search/recommendations',json={'selected_ncs_ids':['skill-server'],'preparation_conversation_id':cid},headers={'Authorization':'Bearer owner-token'})
        self.assertEqual(response.status_code,200,response.text)
        user,loaded_id=repo.load.call_args.args
        self.assertEqual(user.user_id,'owner');self.assertEqual(str(loaded_id),cid)
        self.assertEqual(len(service.recommend.call_args.kwargs['confirmed_experience']),1)
        self.assertNotIn('Redis',str(service.recommend.call_args.kwargs))

    def test_other_owner_missing_or_expired_conversation_never_searches(self):
        client,service=self.client(SimpleNamespace(load=Mock(side_effect=KeyError())))
        response=client.post('/api/job-search/recommendations',json={'selected_ncs_ids':['skill-server'],'preparation_conversation_id':str(uuid4())},headers={'Authorization':'Bearer owner-token'})
        self.assertEqual(response.status_code,404);service.recommend.assert_not_called()

    def test_storage_failure_never_silently_drops_experience(self):
        client,service=self.client(SimpleNamespace(load=Mock(side_effect=SupabasePersistenceError('FAILED','failed'))))
        response=client.post('/api/job-search/recommendations',json={'selected_ncs_ids':['skill-server'],'preparation_conversation_id':str(uuid4())},headers={'Authorization':'Bearer owner-token'})
        self.assertEqual(response.status_code,503);service.recommend.assert_not_called()

    def test_client_cannot_submit_confirmed_facts(self):
        client,service=self.client(SimpleNamespace(load=Mock()))
        response=client.post('/api/job-search/recommendations',json={'selected_ncs_ids':['skill-server'],'confirmed_experience':self.confirmed},headers={'Authorization':'Bearer owner-token'})
        self.assertEqual(response.status_code,422);service.recommend.assert_not_called()
