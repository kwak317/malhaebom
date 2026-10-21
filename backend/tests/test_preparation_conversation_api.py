import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.auth import AuthenticatedUser, create_require_authenticated_user, InvalidAccessToken
from app.core.supabase_settings import SupabaseSettings
from app.routers.preparation_conversation import register_preparation_routes
from app.services.preparation_conversation_repository import PreparationRepository, PreparationConflict


class Verifier:
    def verify_access_token(self, token):
        if token != "test-token": raise InvalidAccessToken()
        return "owner"


class PreparationApiTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.state.coaching_service = SimpleNamespace(provider=None)
        app.state.coaching_observation_sink = SimpleNamespace(record=Mock())
        register_preparation_routes(app, create_require_authenticated_user(Verifier()))
        self.service = SimpleNamespace(respond=Mock(return_value={"conversation_id": str(uuid4()),
            "message": "현재 내용만 설명해요.", "follow_up_question": None, "action": "stay", "status": "ok"}), bind=Mock())
        app.state.preparation_conversation_service = self.service
        self.client = TestClient(app)
        self.request = {"request_id": str(uuid4()), "current_stage": "ncs", "message": "API 개발이 뭐야?"}

    def test_requires_auth_before_generation(self):
        self.assertEqual(self.client.post("/api/agent/preparation", json=self.request).status_code, 401)
        self.service.respond.assert_not_called()

    def test_authenticated_request_and_separate_question(self):
        response = self.client.post("/api/agent/preparation", json=self.request, headers={"Authorization": "Bearer test-token"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["follow_up_question"])
        self.assertEqual(self.service.respond.call_args.args[0].user_id, "owner")

    def test_rejects_client_owner_and_state_injection(self):
        response = self.client.post("/api/agent/preparation", json={**self.request, "user_id": "other", "pending_profile_update": {}},
            headers={"Authorization": "Bearer test-token"})
        self.assertEqual(response.status_code, 422)
        self.service.respond.assert_not_called()


class PreparationRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.response = []
        def handle(request):
            self.requests.append(request)
            return httpx.Response(200, json=self.response)
        http = httpx.Client(transport=httpx.MockTransport(handle))
        self.addCleanup(http.close)
        self.repo = PreparationRepository(SupabaseSettings("https://example.supabase.co", "publishable", "server-key"), http)
        self.user = AuthenticatedUser("owner", "user-token")
        self.cid = uuid4()

    def test_load_always_filters_owner_and_expiry(self):
        with self.assertRaises(KeyError): self.repo.load(self.user, self.cid)
        params = self.requests[0].url.params
        self.assertEqual(params["user_id"], "eq.owner")
        self.assertTrue(params["expires_at"].startswith("gt."))

    def test_save_filters_owner_expiry_and_version_for_atomic_cas(self):
        with self.assertRaises(PreparationConflict):
            self.repo.save(self.user, {"id": str(self.cid), "version": 2}, {})
        params = self.requests[0].url.params
        self.assertEqual(params["version"], "eq.2")
        self.assertEqual(params["user_id"], "eq.owner")
        self.assertTrue(params["expires_at"].startswith("gt."))
