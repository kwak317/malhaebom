import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import create_app
from app.services.coaching_observability import active_coaching_trace, observation_trace_id, LangfuseCoachingObservationSink
from test_coaching_api import FakeVerifier, RecordingObservationSink, valid_request


class RequestTraceTest(unittest.TestCase):
    def setUp(self):
        self.sink = RecordingObservationSink()
        self.sink.record_http_request = Mock()
        with patch.dict("os.environ", {"COACHING_MOCK_ENABLED": "true"}):
            self.app = create_app(token_verifier=FakeVerifier(), coaching_observation_sink=self.sink,
                                  allowed_origins=["https://malhaebom.xyz"])
        self.seen = []
        def respond(user, request):
            self.seen.append([observation_trace_id(), observation_trace_id()])
            return {"conversation_id": str(uuid4()), "message": "확인했어요.",
                    "follow_up_question": None, "action": "stay", "status": "ok"}
        self.service = SimpleNamespace(respond=Mock(side_effect=respond), model_name="test-model", free_chat=False)
        self.app.state.preparation_conversation_service = self.service
        self.client = TestClient(self.app)
        self.body = {"request_id": str(uuid4()), "current_stage": "ncs", "message": "API 역할을 설명해줘"}
        self.auth = {"Authorization": "Bearer owner-token", "Origin": "https://malhaebom.xyz"}

    def assert_link(self, response):
        trace = response.headers["X-Trace-Id"]
        self.assertRegex(trace, r"^[0-9a-f]{32}$")
        self.assertEqual(trace, response.headers["X-Request-Id"])
        self.assertEqual(self.sink.record_http_request.call_args.kwargs["trace_id"], trace)
        self.assertEqual(self.sink.record_http_request.call_args.kwargs["status_code"], response.status_code)
        self.assertIsNone(active_coaching_trace())
        return trace

    def test_preparation_generations_summary_and_header_share_id(self):
        response = self.client.post("/api/agent/preparation", json=self.body, headers=self.auth)
        self.assertEqual(response.status_code, 200)
        trace = self.assert_link(response)
        self.assertEqual(self.seen, [[trace, trace]])
        self.assertEqual(self.sink.items[0].trace_id, trace)
        exposed = response.headers["access-control-expose-headers"].lower()
        self.assertIn("x-trace-id", exposed)
        self.assertIn("x-request-id", exposed)

    def test_each_http_send_has_a_new_id_even_with_reused_payload_id(self):
        first = self.assert_link(self.client.post("/api/agent/preparation", json=self.body, headers=self.auth))
        second = self.assert_link(self.client.post("/api/agent/preparation", json=self.body, headers=self.auth))
        self.assertNotEqual(first, second)

    def test_auth_failure_has_trace_without_model_execution(self):
        response = self.client.post("/api/agent/preparation", json=self.body)
        self.assertEqual(response.status_code, 401)
        self.assert_link(response)
        self.service.respond.assert_not_called()

    def test_invalid_schema_has_trace_without_model_execution(self):
        response = self.client.post("/api/agent/preparation", json={"message": "bad"}, headers=self.auth)
        self.assertEqual(response.status_code, 422)
        self.assert_link(response)
        self.service.respond.assert_not_called()

    def test_conflict_has_trace(self):
        from app.services.preparation_conversation_repository import PreparationConflict
        self.service.respond.side_effect = PreparationConflict("conflict")
        response = self.client.post("/api/agent/preparation", json=self.body, headers=self.auth)
        self.assertEqual(response.status_code, 409)
        self.assert_link(response)

    def test_coaching_header_links_existing_summary(self):
        response = self.client.post("/api/agent", json=valid_request(), headers=self.auth)
        self.assertEqual(response.status_code, 200)
        trace = self.assert_link(response)
        self.assertEqual(self.sink.items[0].trace_id, trace)

    def test_chat_auth_failure_has_trace(self):
        response = self.client.post("/api/agent/chat", json={})
        self.assertEqual(response.status_code, 401)
        self.assert_link(response)

    def test_unexpected_failure_returns_trace_without_error_content(self):
        self.service.respond.side_effect = RuntimeError("sensitive-error-body")
        response = self.client.post("/api/agent/preparation", json=self.body, headers=self.auth)
        self.assertEqual(response.status_code, 500)
        self.assert_link(response)
        self.assertNotIn("sensitive-error-body", response.text)

    def test_interview_chat_success_summary_has_same_id(self):
        from app.schemas.interview_chat import InterviewChatResponse
        seen = []
        def respond(user, request):
            seen.append(observation_trace_id())
            return InterviewChatResponse(conversation_id=uuid4(), status="active", message="검토했어요.", follow_up_question=None, summary=None)
        self.app.state.interview_chat_service = SimpleNamespace(respond=respond, provider=SimpleNamespace(model_name="test-model"))
        body = {"action":"start", "request_id":str(uuid4()), "practice_session_id":str(uuid4())}
        response = self.client.post("/api/agent/chat", json=body, headers=self.auth)
        self.assertEqual(response.status_code, 200)
        trace = self.assert_link(response)
        self.assertEqual(seen, [trace])
        self.assertEqual(self.sink.items[0].trace_id, trace)

    def test_interview_chat_error_summary_has_same_id(self):
        self.app.state.interview_chat_service = SimpleNamespace(respond=Mock(side_effect=KeyError()), provider=SimpleNamespace(model_name="test-model"))
        body = {"action":"start", "request_id":str(uuid4()), "practice_session_id":str(uuid4())}
        response = self.client.post("/api/agent/chat", json=body, headers=self.auth)
        self.assertEqual(response.status_code, 404)
        trace = self.assert_link(response)
        self.assertEqual(self.sink.items[0].trace_id, trace)

    def test_concurrent_requests_do_not_mix_trace_contexts(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barrier, seen = Barrier(2), {}
        def respond(user, request):
            first = observation_trace_id()
            barrier.wait(timeout=5)
            seen[request.message] = (first, observation_trace_id())
            return {"conversation_id":str(uuid4()), "message":request.message, "follow_up_question":None, "action":"stay", "status":"ok"}
        self.service.respond.side_effect = respond
        def send(message):
            client = TestClient(self.app)
            try: return client.post("/api/agent/preparation", json={**self.body,"message":message}, headers=self.auth)
            finally: client.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(send, ["first", "second"]))
        ids = []
        for response in responses:
            self.assertEqual(response.status_code, 200)
            trace = response.headers["X-Trace-Id"]
            self.assertEqual(seen[response.json()["message"]], (trace, trace))
            ids.append(trace)
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual({o.trace_id for o in self.sink.items}, set(ids))
        self.assertIsNone(active_coaching_trace())

    def test_export_is_same_trace_and_omits_sensitive_request_content(self):
        client = Mock()
        sink = LangfuseCoachingObservationSink(client)
        trace = uuid4().hex
        sink.record_http_request(trace_id=trace, method="POST", path="/api/agent/preparation", status_code=200, latency_ms=10)
        call = client.start_observation.call_args.kwargs
        self.assertEqual(call["trace_context"], {"trace_id": trace})
        self.assertEqual(set(call["metadata"]), {"request_id", "method", "path", "http_status", "latency_ms"})
        client.start_observation.return_value.end.assert_called_once()
