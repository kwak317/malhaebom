#!/usr/bin/env bash
# README의 python -m venv / python -m pip install 관례를 따르는 평가 전용 환경.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
eval_venv="$project_root/.venv-llm-eval"
eval_python="${EVAL_PYTHON:-python3.12}"
"$eval_python" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else "Python 3.12가 필요합니다")'
if [[ ! -e "$eval_venv" ]]; then
    "$eval_python" -m venv --without-pip "$eval_venv"
fi
"$eval_venv/bin/python" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) and sys.prefix != sys.base_prefix else "평가 venv는 Python 3.12여야 합니다")'
# Ubuntu의 python3.12-venv 미설치 환경에서도 이미 설치된 uv로 pip만 보완한다.
if ! "$eval_venv/bin/python" -m pip --version >/dev/null 2>&1; then
    if "$eval_venv/bin/python" -c 'import ensurepip' >/dev/null 2>&1; then
        "$eval_venv/bin/python" -m ensurepip --upgrade
    elif command -v uv >/dev/null 2>&1; then
        uv --cache-dir "$project_root/.cache/uv-eval" pip install --python "$eval_venv/bin/python" pip
    else
        printf 'pip bootstrap 불가: python3.12-venv 또는 uv를 설치하세요.\n' >&2
        exit 1
    fi
fi
"$eval_venv/bin/python" -m pip --cache-dir "$project_root/.cache/pip-eval" install -r "$project_root/backend/requirements-eval.txt"
"$eval_venv/bin/python" -m pip check
cd -- "$project_root"
"$eval_venv/bin/python" -B - <<'PY'
import sys
import openai
from evals.environment import load_evaluation_env, resolve_provider_credentials
from evals.run_model_comparison import load_dataset
from app.services.coaching_skill import load_skill_bundle
from app.schemas.coaching import CoachingLLMOutput
from evals.evaluation_records import MODELS
from pathlib import Path
load_evaluation_env()
resolve_provider_credentials(require_openrouter=True)
print('OPENROUTER_API_KEY: 존재 (값 비공개); MODEL_API_KEY는 OpenRouter에서 사용하지 않음')
print('Python:', sys.version.split()[0], 'OpenAI SDK:', openai.__version__)
assert len(load_dataset(Path('evals/dataset.v2.jsonl'))) == 30
load_skill_bundle(Path('skills/interview-coach/SKILL.md'))
CoachingLLMOutput.model_json_schema()
assert len(MODELS) == 6
print('import/dataset/Skill/schema/6종 config: OK')
PY
"$eval_venv/bin/python" -B evals/run_model_comparison.py --help >/dev/null
"$eval_venv/bin/python" -B evals/run_model_comparison.py \
    --candidate baseline=mock:expected --candidate degraded=mock:degraded \
    --output-dir "$project_root/local-results/eval-env-smoke"
printf 'CLI/mock smoke: OK\n평가 venv: %s\n' "$eval_venv"
