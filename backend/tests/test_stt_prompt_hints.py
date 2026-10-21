from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.stt_prompt_hints import build_stt_prompt_hints, extract_tech_terms


class SttPromptHintsTest(unittest.TestCase):
    def test_extracts_terms_from_job_and_requirement_context(self):
        terms = extract_tech_terms(
            [
                "백엔드 엔지니어",
                "Python과 FastAPI 기반 REST API 개발, Docker 환경 경험",
                "PostgreSQL 및 Redis 운영 경험 우대",
            ]
        )

        self.assertEqual(
            terms,
            ("Python", "FastAPI", "REST API", "Docker", "PostgreSQL", "Redis"),
        )

    def test_prefers_specific_term_over_contained_generic_term(self):
        terms = extract_tech_terms(
            ["Spring Boot와 GitHub Actions 기반 CI/CD 경험"]
        )

        self.assertIn("Spring Boot", terms)
        self.assertNotIn("Spring", terms)
        self.assertIn("GitHub Actions", terms)
        self.assertNotIn("Git", terms)

    def test_specific_term_wins_even_when_generic_appears_first(self):
        terms = extract_tech_terms(
            [
                "Spring 경험으로 시작했고 이후 Spring Boot를 사용했습니다. "
                "Git을 먼저 쓰다가 GitHub Actions로 CI/CD를 구성했습니다."
            ]
        )

        self.assertIn("Spring Boot", terms)
        self.assertNotIn("Spring", terms)
        self.assertIn("GitHub Actions", terms)
        self.assertNotIn("GitHub", terms)
        self.assertNotIn("Git", terms)

    def test_limits_prompt_terms(self):
        hints = build_stt_prompt_hints(
            [
                "Python Java Kotlin JavaScript TypeScript React Next.js Node.js "
                "Spring Boot FastAPI PostgreSQL Redis Docker Kubernetes AWS Azure"
            ],
            max_terms=5,
        )

        self.assertEqual(len(hints.terms), 5)
        self.assertIsNotNone(hints.initial_prompt)
        self.assertEqual(hints.initial_prompt.count(","), 4)

    def test_no_matching_context_returns_no_prompt(self):
        hints = build_stt_prompt_hints(
            ["문제 해결 경험과 협업 과정에 대해 설명해 주세요."]
        )

        self.assertEqual(hints.terms, ())
        self.assertIsNone(hints.initial_prompt)


if __name__ == "__main__":
    unittest.main()
