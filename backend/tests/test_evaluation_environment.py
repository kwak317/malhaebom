"""실제 API 없이 dotenv/키 선택 정책을 검증한다."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from evals.environment import load_evaluation_env, resolve_provider_credentials

class EvaluationEnvironmentTest(unittest.TestCase):
    def test_dotenv_preserves_shell_and_loads_missing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'.env'
            path.write_text('OPENROUTER_API_KEY=file-test-key\nMODEL_API_KEY=file-other-key\n')
            with patch.dict(os.environ,{'MODEL_API_KEY':'shell-other-key'},clear=True):
                load_evaluation_env(path)
                self.assertEqual(os.environ['MODEL_API_KEY'],'shell-other-key')
                self.assertEqual(resolve_provider_credentials()[0],'file-test-key')

    def test_openrouter_never_falls_back_to_other_keys(self):
        with patch.dict(os.environ,{'MODEL_API_KEY':'other','OPENAI_API_KEY':'other'},clear=True):
            with self.assertRaisesRegex(ValueError,'OPENROUTER_API_KEY'):
                resolve_provider_credentials()
        with patch.dict(os.environ,{'MODEL_API_KEY':'other','OPENROUTER_API_KEY':'router'},clear=True):
            self.assertEqual(resolve_provider_credentials(require_openrouter=True)[0],'router')

    def test_custom_endpoint_keeps_priority_but_six_models_rejects_it(self):
        with patch.dict(os.environ,{'MODEL_API_BASE_URL':'https://example.test/v1',
                                   'MODEL_API_KEY':'custom','OPENROUTER_API_KEY':'router'},clear=True):
            self.assertEqual(resolve_provider_credentials()[0],'custom')
            with self.assertRaises(ValueError):
                resolve_provider_credentials(require_openrouter=True)

    def test_openrouter_rejects_insecure_endpoint(self):
        with patch.dict(os.environ,{'MODEL_API_BASE_URL':'http://openrouter.ai/api/v1',
                                   'OPENROUTER_API_KEY':'router'},clear=True):
            with self.assertRaises(ValueError):
                resolve_provider_credentials()
