# Worklog — 사용자 제공 코칭 시스템 프롬프트 PR

- 일시: 2026-10-01 KST
- 요청: 제공 프롬프트로 교체한 변경을 PR로 생성하고 병합하지 않음
- 기준: GitHub main `459d79a`
- 브랜치: `codex/user-coaching-system-prompt`

## 목적 / 작업 전 상태

기존 로컬 프로젝트에는 다른 작업의 다수 미커밋 변경이 있다. 최신 원격 main에서 별도 worktree를 만들고 이번 코칭 프롬프트만 추출했다. 원격에 없는 다른 실험 후보와 로컬 .env는 포함하지 않는다.

## 변경

- 첨부 영문 원문을 `prompts/coaching-user-supplied-v4-verification.md`에 추가. 마지막 개행 외 본문은 동일하다.
- 코칭 빌더에 해당 버전의 파일 선택 분기를 추가하고 기본값과 .env.example을 맞춤. 기존 v4.2/과거 빌더는 유지.
- 기본 로더의 Skill 결합 회귀 테스트와 Langfuse fallback 버전 기대치를 갱신.
- Spec, CURRENT_STATE, 이 Worklog에 적용 범위와 검증 한계를 기록.

## 검증

기존 Python 3.13 test-venv에서 env -i, PYTHONPATH=.:backend:backend/tests, PYTHONDONTWRITEBYTECODE=1, STT_WARMUP_ENABLED=false로 실행했다. 외부 provider 호출은 없다.

- `python -m unittest tests.test_coaching_prompt tests.test_prompt_skill_separation tests.test_coaching_runtime tests.test_coaching_validation`: 55 tests OK.
- `python -m unittest discover -s backend/tests -p 'test_*.py'`: 570 tests OK.
- `python -m pytest backend/tests -q`: 기존 venv에 pytest가 없어 실행 불가(`No module named pytest`). GitHub Product CI가 pytest를 설치하고 실행한다.
- 첨부 내용 일치, 이전 빌더 hash 보존, 기본 프롬프트와 현재 Skill 결합 검사 통과.
- `git diff --check`: 통과. PR size policy는 commit 후 origin/main 대비 검사한다.

## 한계

이 변경은 기본 프롬프트 선택이며 서버의 단일 호출 구조를 유지한다. 이전 로컬 두 단계 후보 실험은 범주별 품질 기준을 통과하지 못했다. 실제 모델 품질 개선, 로그인 사용자 E2E, 컨테이너 교체, Langfuse 게시와 배포를 검증하거나 수행하지 않았다. 기존 명시적 COACHING_PROMPT_VERSION 또는 Langfuse 설정을 가진 환경은 기존 선택을 유지할 수 있다.

## 다음 작업

PR 리뷰와 CI 확인. 사용자 요청에 따라 병합하지 않는다.
