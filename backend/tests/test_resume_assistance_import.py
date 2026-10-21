import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.services.resume_analysis import MAX_PDF_BYTES, extract_resume_pages
from app.services.resume_assistance import ResumeAssistanceService
from app.services.resume_assistance_routes import register_resume_assistance_routes
from backend.tests.test_resume_analysis import pdf


class ResumeAssistanceImportTest(unittest.TestCase):
    def test_extraction_preserves_contacts_only_with_explicit_opt_out(self):
        data = pdf("Name: Example\nEmail: person@example.com\nSpring Boot API development")
        redacted = "\n".join(extract_resume_pages(data))
        self.assertNotIn("Example", redacted)
        self.assertNotIn("person@example.com", redacted)
        original = "\n".join(extract_resume_pages(data, redact_private=False))
        self.assertIn("Name: Example", original)
        self.assertIn("person@example.com", original)

    def test_import_real_pdf_preserves_grounded_form_values(self):
        service = ResumeAssistanceService(key="test")
        data = pdf("Name: Example\nEmail: person@example.com\nSpring Boot API development")
        output = {"items": [
            {"field": "name", "source_excerpt": "Example"},
            {"field": "email", "source_excerpt": "person@example.com"},
            {"field": "technology", "source_excerpt": "Spring Boot API development"},
        ]}
        with patch.object(service, "generate", return_value=output) as generate:
            result = service.import_pdf(data)
        self.assertEqual([item["value"] for item in result["items"]],
                         ["Example", "person@example.com", "Spring Boot API development"])
        self.assertIn("person@example.com", generate.call_args.args[1])
        self.assertEqual(result["omitted_items"], 0)

    def test_unredacted_extraction_keeps_pdf_validation(self):
        for data in (b"not pdf", b"%PDF-" + b"x" * MAX_PDF_BYTES,
                     pdf(encrypted=True), pdf(text=""), pdf(pages=11)):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                extract_resume_pages(data, redact_private=False)

    def test_import_route_consent_validation_and_cors(self):
        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI()
        app.add_middleware(CORSMiddleware, allow_origins=["https://malhaebom.xyz"],
                           allow_methods=["POST"], allow_headers=["*"])
        register_resume_assistance_routes(app, lambda: "test-owner")
        client = TestClient(app)
        headers = {"Origin": "https://malhaebom.xyz"}
        output = {"items": [{"field": "technology", "source_excerpt": "Spring Boot API development"}]}
        with patch.object(ResumeAssistanceService, "generate", return_value=output) as generate:
            denied = client.post("/api/resume/assist/import", headers=headers,
                                 data={"consent": "false"}, files={"file": ("resume.pdf", pdf())})
            self.assertEqual(denied.status_code, 403)
            generate.assert_not_called()
            invalid = client.post("/api/resume/assist/import", headers=headers,
                                  data={"consent": "true"}, files={"file": ("resume.txt", b"not pdf")})
            self.assertEqual(invalid.status_code, 422)
            generate.assert_not_called()
            response = client.post("/api/resume/assist/import", headers=headers,
                                   data={"consent": "true"}, files={"file": ("resume.pdf", pdf())})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["access-control-allow-origin"], "https://malhaebom.xyz")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.json()["items"][0]["value"], "Spring Boot API development")

    def test_import_route_requires_auth_before_provider(self):
        app = FastAPI()

        def deny():
            raise HTTPException(status_code=401, detail="Login required")

        register_resume_assistance_routes(app, deny)
        with patch.object(ResumeAssistanceService, "generate") as generate:
            response = TestClient(app).post("/api/resume/assist/import",
                                           data={"consent": "true"}, files={"file": ("resume.pdf", pdf())})
        self.assertEqual(response.status_code, 401)
        generate.assert_not_called()
