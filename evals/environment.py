"""평가 전용 환경 로딩과 endpoint별 키 선택. 키 값은 로깅하지 않는다."""
import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'


def load_evaluation_env(env_file=None):
    return load_dotenv(env_file or PROJECT_ROOT / '.env', override=False)


def resolve_provider_credentials(*, require_openrouter=False):
    base_url = os.getenv('MODEL_API_BASE_URL', '').strip() or OPENROUTER_BASE_URL
    parsed = urlparse(base_url)
    is_openrouter = parsed.hostname == 'openrouter.ai'
    if require_openrouter and not is_openrouter:
        raise ValueError('6종 평가는 OpenRouter endpoint를 사용해야 합니다')
    if is_openrouter:
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None,443):
            raise ValueError('OpenRouter endpoint는 HTTPS 기본 포트를 사용해야 합니다')
        key = os.getenv('OPENROUTER_API_KEY', '').strip()
        if not key:
            raise ValueError('OPENROUTER_API_KEY가 필요합니다 (.env 또는 실행 환경)')
    else:
        key = (os.getenv('MODEL_API_KEY', '').strip() or
               os.getenv('OPENROUTER_API_KEY', '').strip() or
               os.getenv('OPENAI_API_KEY', '').strip())
        if not key:
            raise ValueError('사용자 지정 endpoint에는 MODEL_API_KEY 등이 필요합니다')
    return key, base_url
