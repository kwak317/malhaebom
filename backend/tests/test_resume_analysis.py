import io
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from pydantic import ValidationError

from app.main import create_app
from app.schemas.resume import ConfirmedResumeProfile
from app.schemas.saramin_recommendation import SaraminRecommendationRequest
from app.services.resume_analysis import (
    MAX_PDF_BYTES, ResumeAnalysisService, ResumeAnalysisUnavailable,
    build_resume_analysis_service_from_env, extract_resume_pages, redact_resume_text,
)
from backend.tests.test_saramin_recommendation import FakeSearch, FakeVerifier, FakeVerifierToken
from app.services.saramin_recommendation import SaraminRecommendationService


def pdf(text="Spring Boot API development", pages=1, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(612, 792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\n", ") Tj 0 -20 Td (")
        stream.set_data(f"BT /F1 12 Tf 50 700 Td ({escaped}) Tj ET".encode())
        page[NameObject("/Contents")] = stream
    if encrypted:
        writer.encrypt("secret")
    output = io.BytesIO(); writer.write(output)
    return output.getvalue()


class Provider:
    model_name = "google/gemini-3.1-flash-lite"

    def __init__(self, facts=None):
        self.facts = facts if facts is not None else [{"category": "technology", "value": "Spring Boot API development", "keyword": "Spring Boot", "page": 1, "source_excerpt": "Spring Boot API development"}]
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return {"facts": self.facts}


class ResumeAnalysisTest(unittest.TestCase):
    def test_real_pdf_extraction_and_contact_redaction_before_provider(self):
        provider = Provider()
        result = ResumeAnalysisService(provider).analyze(pdf("Name: Example\nEmail: person@example.com\n010-1234-5678\nSpring Boot API development"))
        self.assertEqual(result.model, "google/gemini-3.1-flash-lite")
        self.assertEqual(result.facts[0].page, 1)
        prompt = provider.calls[0]["user_prompt"]
        self.assertNotIn("person@example.com", prompt)
        self.assertNotIn("Example", prompt)
        self.assertNotIn("010-1234-5678", prompt)

    def test_six_categories_grounded_in_their_page(self):
        facts = [{"category": category, "value": "Spring Boot API development", "keyword": "Spring Boot" if category == "technology" else None, "page": 1, "source_excerpt": "Spring Boot API development"} for category in ("role", "career", "technology", "project", "education", "qualification")]
        self.assertEqual(len(ResumeAnalysisService(Provider(facts)).analyze(pdf()).facts), 6)

    def test_rejects_invalid_oversized_encrypted_scanned_and_page_limit(self):
        for data in (b"not pdf", b"%PDF-" + b"x" * MAX_PDF_BYTES, pdf(encrypted=True), pdf(text=""), pdf(pages=11)):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                extract_resume_pages(data)

    def test_mixed_image_page_is_not_silently_skipped(self):
        writer = PdfWriter(); writer.append(io.BytesIO(pdf())); writer.add_blank_page(612, 792)
        buffer = io.BytesIO(); writer.write(buffer)
        with self.assertRaisesRegex(ValueError, "읽을 수 없는 페이지"):
            extract_resume_pages(buffer.getvalue())

    def test_rejects_hallucinated_quote_page_and_keyword_and_pii(self):
        for patch_value in ({"source_excerpt": "made up"}, {"value": "실무 경력 5년"}, {"page": 2}, {"keyword": "Python"}, {"value": "person@example.com"}, {"category": "name"}):
            provider = Provider(); provider.facts[0].update(patch_value)
            with self.subTest(patch=patch_value), self.assertRaises(ResumeAnalysisUnavailable):
                ResumeAnalysisService(provider).analyze(pdf())
            self.assertEqual(len(provider.calls), 2)

    def test_confirmed_profile_rejects_contact_and_nontech_search_keyword(self):
        for fact in ({"category": "technology", "value": "person@example.com", "keyword": "Spring Boot"}, {"category": "career", "value": "인턴", "keyword": "회사"}, {"category": "technology", "value": "기술", "keyword": ""}):
            with self.assertRaises(ValidationError):
                ConfirmedResumeProfile(facts=[fact])

    def test_builder_uses_same_model_and_bounded_tokens(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test"}), patch("app.services.resume_analysis.OpenAICompatibleJsonProvider") as factory:
            build_resume_analysis_service_from_env()
        self.assertEqual(factory.call_args.kwargs["model_name"], "google/gemini-3.1-flash-lite")
        self.assertEqual(factory.call_args.kwargs["max_tokens"], 4096)

    def test_api_requires_auth_handles_invalid_file_and_returns_analysis(self):
        client = TestClient(create_app(token_verifier=FakeVerifierToken(), resume_analysis_service=ResumeAnalysisService(Provider())))
        self.assertEqual(client.post("/api/resume/analyze", files={"file": ("resume.pdf", pdf())}).status_code, 401)
        headers = {"Authorization": "Bearer owner-token"}
        self.assertEqual(client.post("/api/resume/analyze", headers=headers, files={"file": ("resume.txt", b"text")}).status_code, 422)
        result = client.post("/api/resume/analyze", headers=headers, files={"file": ("resume.pdf", pdf())})
        self.assertEqual(result.status_code, 200, result.text)

    def test_confirmed_resume_without_readme_drives_search_and_keeps_source_labels(self):
        search = FakeSearch()
        profile = ConfirmedResumeProfile(facts=[{"category": "technology", "value": "Spring Boot 사용", "keyword": "Spring Boot"}, {"category": "career", "value": "회사 인턴 3개월", "keyword": None}])
        result = SaraminRecommendationService(search, FakeVerifier()).recommend(SaraminRecommendationRequest(selected_ncs_ids=["skill-server"], resume_profile=profile))
        self.assertEqual(search.technologies, ["Spring Boot"])
        self.assertTrue(result.recommendations)
        self.assertEqual(result.recommendations[0].matched_resume_technologies, ["Spring Boot"])
        self.assertEqual(result.recommendations[0].matched_technologies, [])


if __name__ == "__main__":
    unittest.main()
