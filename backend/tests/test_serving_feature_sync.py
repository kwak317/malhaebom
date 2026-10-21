"""Operating feature boundaries retained during source synchronization."""
import hashlib
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.services.coaching_questions import get_custom_coaching_question
from app.services.resume_assistance import AssistanceUnavailable, PolishRequest, ResumeAssistanceService
from app.services.resume_assistance_routes import register_resume_assistance_routes


def test_saved_custom_question_retains_text_and_its_three_criteria():
    text = "트랜잭션의 원자성이 무엇인가요?"
    identifier = "custom-" + hashlib.md5(text.encode()).hexdigest()[:12]
    question = get_custom_coaching_question(identifier, text)
    assert question.text == text
    assert question.question_type == "custom_interview"
    assert question.active_criterion_ids == ["question_focus", "answer_rationale", "concrete_support"]
    assert get_custom_coaching_question(identifier, "다른 질문") is None


@pytest.mark.parametrize("value", ["이메일: person@example.com", "전화: 010-1234-5678", "번호: 900101-1234567", "a" * 2001])
def test_polish_rejects_private_or_oversized_text_before_provider(value):
    service = ResumeAssistanceService()
    service.generate = Mock()
    with pytest.raises(ValueError):
        service.polish(PolishRequest(consent=True, fields={"action": value}))
    service.generate.assert_not_called()


def test_polish_rejects_invented_numbers_without_applying_the_change():
    service = ResumeAssistanceService()
    service.generate = Mock(return_value={"items": [{"field": "action", "value": "응답 시간을 50% 줄였습니다.", "source_excerpt": "캐시 적용"}], "questions": []})
    with pytest.raises(AssistanceUnavailable):
        service.polish(PolishRequest(consent=True, fields={"action": "캐시 적용"}))


@pytest.mark.parametrize("path,payload", [("/api/resume/assist/polish", {"consent": True, "fields": {"action": "캐시 적용"}}), ("/api/resume/assist/import", None)])
def test_resume_assistance_requires_authenticated_user(path, payload):
    app = FastAPI()
    def unauthenticated():
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    register_resume_assistance_routes(app, unauthenticated)
    client = TestClient(app)
    response = client.post(path, json=payload) if payload else client.post(path, data={"consent": "true"}, files={"file": ("resume.pdf", b"%PDF", "application/pdf")})
    assert response.status_code == 401


def test_pdf_import_without_consent_is_rejected_before_parsing():
    app = FastAPI()
    register_resume_assistance_routes(app, lambda: object())
    response = TestClient(app).post("/api/resume/assist/import", data={"consent": "false"}, files={"file": ("resume.pdf", b"%PDF", "application/pdf")})
    assert response.status_code == 403


@pytest.mark.parametrize("path,payload", [("/api/resume/assist/polish", {"consent": True, "fields": {"action": "캐시 적용"}}), ("/api/resume/assist/import", None)])
def test_application_middleware_preserves_assistance_authentication(path, payload):
    from app.main import create_app
    client = TestClient(create_app())
    response = client.post(path, json=payload) if payload else client.post(path, data={"consent": "true"}, files={"file": ("resume.pdf", b"%PDF", "application/pdf")})
    assert response.status_code == 401
