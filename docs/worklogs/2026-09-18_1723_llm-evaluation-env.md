# Worklog — Python 3.12 LLM 평가 전용 환경

- 일시: 2026-09-18
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음; feat/llm-evaluation-foundation에서 이전 변경 보존
- 관련 요구사항/결정: coaching-evaluation-ops AC-14/15, 사용자 전용 setup 요청

## 1. 목적

프로젝트 로컬 Python 3.12 venv와 반복 가능한 setup, 안전한 .env/키 선택을 제공한다. 실제 LLM 요청 제외.

## 2. 작업 전 상태

별도 setup/venv 셸 스크립트는 없었다. README의 python -m venv 및 python -m pip install -r 방식을 확인했다.
기본 Conda Python 3.14에는 OpenAI SDK가 없었고 임시 테스트 환경의 SDK 2.x는 운영 요구 범위와 달랐다.
runner는 .env를 읽지 않고 MODEL_API_KEY를 먼저 선택했다. 필수 프로젝트 문서와 evals README를 확인했다.

## 3. 수행 내용

- evals/setup_env.sh: Python 3.12 검사, .venv-llm-eval 생성/재사용, pip bootstrap, 공유 경량 의존성 설치, pip check/import/help/mock 검사.
- 시스템 /usr/bin/python3.12에서 ensurepip 부재를 확인했다. --without-pip 생성 후 이미 설치된 uv로 pip만 설치하는 경로를 사용했다.
- 운영 requirements의 네 기존 버전 제약을 requirements-eval.txt로 분리하고 전체 backend requirements가 이를 포함하게 했다. 기존 버전 범위는 동일하다.
- .gitignore에 venv 추가. uv/pip 캐시는 기존 무시되는 프로젝트 .cache 아래로 지정했다.
- environment.py와 CLI 연동: 루트 .env override=False, OpenRouter 전용 키 선택, HTTPS 제한, six-models endpoint 검사. 다른 endpoint의 기존 키 우선순위 유지.
- 관련 테스트와 기준 문서 갱신.

## 주요 판단과 이유

기존 전체 requirements에는 STT/TTS/ML 의존성이 있어 평가에는 네 경량 패키지만 설치한다.
처음 전체 requirements를 constraint로 재사용했으나 extras가 포함되어 pip가 거부했다. 동일 버전 목록을 공유 requirements로 분리했다.
OpenRouter에서 타 서비스 MODEL_API_KEY를 선택할 수 없도록 OPENROUTER_API_KEY만 선택한다. 키 값은 출력하지 않았다.

## 4. 변경 파일

- evals/setup_env.sh, evals/environment.py, evals/run_model_comparison.py
- backend/requirements-eval.txt, backend/requirements.txt
- backend/tests/test_evaluation_environment.py, .gitignore
- evals/README.md, docs/CURRENT_STATE.md, docs/DECISIONS.md, docs/specs/coaching-evaluation-ops.md, 본 Worklog

## 5. 검증

- bash -n evals/setup_env.sh: 통과.
- setup 최초 성공 및 두 번 재실행 성공: Python 3.12.3 / OpenAI SDK 1.109.1 / pip check 통과.
- 실제 사용 venv: /home/nanocode/proj2-3/.venv-llm-eval. Conda/임시 환경으로 평가하지 않았다.
- 전용 venv에서 test_coaching_eval/test_coaching_eval_v2/test_evaluation_environment/test_evaluation_records: 21개 통과.
- setup mock: 30건×2후보=60 실행, local-results/eval-env-smoke JSON/Markdown 생성.
- six-models 실제 adapter를 mock으로 교체한 CLI smoke: 6개 모델/config/키 연결 및 180건 mock 실행 성공. 임시 보고서 정리.
- dataset v2/Skill/schema/6종 config 로딩 성공. .env 키 존재 확인, 값 비공개.
- git diff --check 통과. venv/결과는 Git ignore 확인.

## 6. 발견한 문제 / 남은 리스크

초기 sandbox 설치는 uv 홈 캐시 권한/DNS 제한으로 실패했다. 프로젝트 캐시 경로 지정 후 자동 승인된 의존성 설치로 해결했다.
광범위 test_*eval*.py 패턴은 TTS 평가 테스트까지 포함해 numpy 누락으로 실패했다. 평가 전용 환경에 ML 패키지를 추가하지 않고 대상 네 모듈을 명시해 21개 테스트를 재실행했다.

## 미확인 사항

실제 OpenRouter 인증/모델 가용성/품질/가격은 확인하지 않았다. 전체 서비스/음성/프런트엔드 테스트는 이번 경량 환경에서 실행하지 않았다.
패치 버전은 requirements 범위 내 설치 시점에 따라 달라진다. 기존 API 전체 의존성 목록은 버전 변경 없이 공유 파일을 포함하는 구조로 유지된다.

## 7. 다음 작업

전용 venv를 활성화하고 승인된 실제 평가를 실행한다. setup 자체에는 실제 모델 호출이 없다.
