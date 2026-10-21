from __future__ import annotations

import json
import os
import re
import sys
import unittest
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for path in (PROJECT_ROOT, PROJECT_ROOT / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.core.supabase_settings import SupabaseSettings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.coaching_questions import (  # noqa: E402
    PRESET_QUESTION_IDS, get_preset_coaching_question,
)
from app.services.coaching_runtime import McpLlmCoachingService  # noqa: E402
from app.services.coaching_skill import CoachingSkillError, load_skill_bundle  # noqa: E402
from app.services.mcp_access import McpAccessTokenCodec  # noqa: E402
from app.services.mcp_context_gateway import McpStdioContextGateway  # noqa: E402
from app.services.practice_history import coaching_content_analysis_from_response  # noqa: E402
from app.services.supabase_coaching_context import SupabaseCoachingContextRepository  # noqa: E402
from test_coaching_api import FakeVerifier  # noqa: E402


JOB_ID = "80000000-0000-4000-8000-000000000001"
SESSION_ID = "90000000-0000-4000-8000-000000000001"


class ContractOnlyProvider:
    """의미 품질 대신 질문별 ID·출력 계약의 연결만 검사한다."""

    model_name = "test:contract-only"

    def __init__(self):
        self.contexts = []

    def generate(self, *, system_prompt, user_prompt, schema, contract_attempt):
        context = json.loads(user_prompt.split("\n", 1)[1])
        self.contexts.append(context)
        ids = context["question"]["active_criterion_ids"]
        return {
            "job_alignment": [{"requirement_id": "J01-R1", "label": "insufficient_evidence", "reason": "개발용 입력에는 경험 설명이 없습니다.", "evidence": []}],
            "intent_assessment": {"label": "undetermined", "reason": "개발용 입력만으로 질문 적합성을 판단할 수 없습니다."},
            "criterion_assessments": [{"criterion_id": cid, "assessment": "not_observed", "reason": "개발용 입력에는 관련 설명이 없습니다.", "evidence": [], "needed": "본인의 실제 경험이나 계획을 설명해 주세요."} for cid in ids],
            "clarifying_question": "본인의 실제 경험이나 계획을 설명해 주시겠어요?",
            "next_actions": [{"target_type": "criterion", "target_id": ids[0], "action": "선택한 질문에 맞는 본인의 경험이나 계획을 한 문장으로 설명해 보세요."}],
            "example_answer": "[선택한 질문에 맞는 본인의 경험이나 계획]을 설명하겠습니다.",
        }


class ContextRestFixture(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query)
        now = datetime.now(UTC)
        expires = (now + timedelta(hours=1)).isoformat()
        if parsed.path.endswith("/answer_revisions"):
            revision_id = query["id"][0].removeprefix("eq.")
            number = int(revision_id[-2:])
            rows = [{"id": revision_id, "user_id": "user-owner", "practice_session_id": SESSION_ID, "question_id": f"preset-{number:02d}", "answer_segments": [{"segment_id": "s1", "text": "개발용 계약 연결 입력입니다."}], "delivery_metrics": {}, "confirmed_at": now.isoformat(), "expires_at": expires}]
        elif parsed.path.endswith("/practice_sessions"):
            rows = [{"id": SESSION_ID, "user_id": "user-owner", "job_posting_id": JOB_ID, "expires_at": expires}]
        elif parsed.path.endswith("/job_postings"):
            rows = [{"id": JOB_ID, "source_url": "https://example.invalid/test", "captured_at": now.isoformat(), "review_status": "reviewed"}]
        elif parsed.path.endswith("/practice_session_requirements"):
            rows = [{"requirement_id": "test-requirement", "job_requirements": {"code": "J01-R1", "requirement_text": "웹 서비스 개발 경험"}}]
        else:
            self.send_error(404)
            return
        body = json.dumps(rows).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


class PresetCoachingTest(unittest.TestCase):
    def test_catalog_matches_every_visible_question_and_skill(self):
        text = (PROJECT_ROOT / "frontend/src/catalog/presetQuestions.ts").read_text(
            encoding="utf-8"
        )
        visible = dict(re.findall(r'id: "([^"]+)", text: "([^"]+)"', text))
        self.assertEqual(set(visible), PRESET_QUESTION_IDS)
        bundle = load_skill_bundle()
        repository = SupabaseCoachingContextRepository(SupabaseSettings("https://example.invalid", "test", "test-secret"))
        for question_id, question_text in visible.items():
            with self.subTest(question_id=question_id):
                question = repository.get_question(question_id)
                self.assertEqual(question.text, question_text)
                bundle.validate_question_context(question)
                if question_id == "preset-04":
                    self.assertEqual(question.criteria_version, "problem-solving-v4-draft.3")
                    self.assertEqual(len(question.active_criterion_ids), 6)
                else:
                    self.assertEqual(question.criteria_version, "preset-interview-v1")
                    self.assertEqual(len(question.active_criterion_ids), 3)
                    self.assertNotIn("cause_inference", question.active_criterion_ids)
        self.assertIsNone(repository.get_question("preset-11"))
        self.assertIsNone(repository.get_question("custom-test"))

    def test_intro_rejects_problem_solving_criteria_and_wrong_version(self):
        question = get_preset_coaching_question("preset-01")
        for changes in ({"active_criterion_ids": ["cause_observation"]}, {"criteria_version": "problem-solving-v4-draft.3"}):
            with self.subTest(changes=changes), self.assertRaises(CoachingSkillError):
                load_skill_bundle().validate_question_context(question.model_copy(update=changes))

    def test_all_visible_questions_reach_provider_via_real_mcp_and_rest(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), ContextRestFixture)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        secret = "test-only-secret-with-at-least-32-characters"
        provider = ContractOnlyProvider()
        try:
            with patch.dict(os.environ, {"COACHING_MOCK_ENABLED": "false", "MCP_INTERNAL_SECRET": secret, "SUPABASE_URL": f"http://127.0.0.1:{server.server_port}", "SUPABASE_PUBLISHABLE_KEY": "test", "SUPABASE_SERVICE_ROLE_KEY": "test-secret", "LANGFUSE_PROMPT_NAME": ""}):
                service = McpLlmCoachingService(McpStdioContextGateway(McpAccessTokenCodec(secret), timeout_seconds=20), provider)
                with TestClient(create_app(token_verifier=FakeVerifier(), coaching_service=service)) as client:
                    for number in range(1, 11):
                        question_id = f"preset-{number:02d}"
                        with self.subTest(question_id=question_id):
                            response = client.post("/api/agent", headers={"Authorization": "Bearer owner-token"}, json={"action": "analyze", "question_id": question_id, "answer_revision_id": f"70000000-0000-4000-8000-{number:012d}", "job_snapshot_id": JOB_ID})
                            self.assertEqual(response.status_code, 200, response.text)
                            body = response.json()
                            self.assertEqual(body["status"], "needs_more_info")
                            expected = get_preset_coaching_question(question_id).active_criterion_ids
                            self.assertEqual([item["criterion_id"] for item in body["criterion_assessments"]], expected)
                            content = coaching_content_analysis_from_response(body, "개발용 계약 연결 입력입니다.")
                            self.assertTrue(all(item["description"] != item["criterion_id"] for item in content["criteria"]))
                    mismatched = client.post("/api/agent", headers={"Authorization": "Bearer owner-token"}, json={"action": "analyze", "question_id": "preset-05", "answer_revision_id": "70000000-0000-4000-8000-000000000001", "job_snapshot_id": JOB_ID})
                    self.assertEqual(mismatched.status_code, 503)
                    self.assertEqual(len(provider.contexts), 10)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
