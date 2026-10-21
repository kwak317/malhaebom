from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.main as main
from app.services.persistent_analysis_jobs import PersistentAnalysisJobService
from app.services.question_rubric_generator import OllamaQuestionRubricGenerator, QuestionRubricUnavailableError


class QuestionFeedbackIntegrationTest(unittest.TestCase):
    def test_rubric_catalog_uses_frontend_preset_ids(self):
        generator = OllamaQuestionRubricGenerator()

        rubric = generator.get_preset("preset-01")

        self.assertIsNotNone(rubric)
        self.assertEqual(rubric["question"], "자기소개를 해주세요.")
        self.assertIsNone(generator.get_preset("1"))

    def test_disabled_feedback_does_not_create_generator(self):
        self.assertTrue(hasattr(main, "_create_question_feedback_generator"))
        factory = getattr(main, "_create_question_feedback_generator", None)
        if factory is None:
            return

        with patch.dict(os.environ, {"LLM_FEEDBACK_ENABLED": "false"}, clear=False):
            self.assertIsNone(factory())

    def test_enabled_feedback_attaches_generator_to_persistent_service(self):
        self.assertTrue(hasattr(main, "_create_question_feedback_generator"))
        if not hasattr(main, "_create_question_feedback_generator"):
            return
        generator = object()

        with (
            patch.dict(os.environ, {"LLM_FEEDBACK_ENABLED": "true"}, clear=False),
            patch("app.main.SupabaseSettings.from_env", return_value=object()),
            patch("app.main.SupabaseAnalysisRepository", return_value=object()),
            patch("app.main.FasterWhisperTranscriber", return_value=object()),
            patch("app.main.SileroVadDetector", return_value=object()),
            patch("app.main.OllamaQuestionRubricGenerator", return_value=generator),
        ):
            app = main.create_app(token_verifier=object(), preset_question_audio_service=object())

        self.assertIsInstance(app.state.analysis_jobs, PersistentAnalysisJobService)
        self.assertIs(app.state.analysis_jobs.question_feedback_generator, generator)

    def test_unavailable_generator_does_not_block_persistent_service_setup(self):
        self.assertTrue(hasattr(main, "_create_question_feedback_generator"))
        factory = getattr(main, "_create_question_feedback_generator", None)
        if factory is None:
            return

        with (
            patch.dict(os.environ, {"LLM_FEEDBACK_ENABLED": "true"}, clear=False),
            patch("app.main.OllamaQuestionRubricGenerator", side_effect=QuestionRubricUnavailableError()),
        ):
            self.assertIsNone(factory())

    def test_invalid_generator_configuration_does_not_block_persistent_service_setup(self):
        factory = main._create_question_feedback_generator
        result: object | None = "raised"

        with (
            patch.dict(os.environ, {"LLM_FEEDBACK_ENABLED": "true"}, clear=False),
            patch("app.main.OllamaQuestionRubricGenerator", side_effect=ValueError("invalid timeout")),
        ):
            try:
                result = factory()
            except ValueError:
                pass

        self.assertIsNone(result)
