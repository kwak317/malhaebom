# Worklog — PR #156 Prompt 중복 확인

- 일시: 2026-10-02 11:31 KST
- 작업자/에이전트: Codex
- 관련 PR: #156 후속 정리
- 관련 요구사항/결정: 과거 Prompt·실험 재현성 보존

## 1. 목적

PR #156에서 추가한 intent 지침의 중복과 Gemini 출력 형식 원인 기록을 확인하고, 현재 사용 경로의 혼동을 줄인다.

## 2. 작업 전 상태

- `prompts/coaching-user-supplied-v4-verification.md`의 intent 지침에 의미가 겹치는 문장이 있다. 이 템플릿은 PR #156의 30건 평가에 사용됐고 현재 기본 Prompt는 `coaching-v5-skill-owned`다.
- `backend/tests/test_coaching_prompt.py`의 기본 Prompt 테스트 두 개는 v5 내용을 검증하지만 이름에 과거 user-supplied v4가 남아 있었다.
- PR #156의 첫 수정 직전(`c16b413^`) `build_response_format`은 Gemini에 `json_object`를 요청했다. 이후 병합된 `main`에는 Gemini JSON Schema 특례가 있었으므로 최종 PR diff만으로 최초 원인을 판단하면 틀릴 수 있다.

## 3. 수행 내용

- 기본 Prompt 테스트 이름을 현재 v5 경로와 맞췄다. 검증 내용은 유지했다.
- PR #156 실험 문서에 v4 원문을 재현을 위해 보존한다는 설명을 추가했다.
- 당시 입력을 바꾸지 않기 위해 v4 템플릿과 모델 결과 수치는 수정하지 않았다.

## 주요 판단과 이유

v4의 중복 문장을 삭제하면 이미 기록된 30건 평가의 Prompt 버전 내용과 해시가 달라진다. 현재 기본 v5는 판정 규칙을 고정 Skill에 위임하고 있으므로 운영 기본 경로에서 같은 중복이 반복되지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/tests/test_coaching_prompt.py` | 기본 v5 Prompt 테스트 이름 정정 |
| `docs/experiments/2026-10-02_gemini-structured-output-reevaluation.md` | 과거 v4 입력 보존 이유 명시 |
| 본 파일 | 확인 근거와 검증 기록 |

## 5. 검증

```text
PYTHONPATH=/tmp/pr156-test-deps /home/nanocode/miniconda3/envs/est/bin/python -m unittest backend.tests.test_coaching_prompt backend.tests.test_coaching_eval: 22 passed
/home/nanocode/miniconda3/envs/est/bin/python -m unittest backend.tests.test_coaching_eval: 12 passed
PYTHONPATH=backend:. /home/nanocode/miniconda3/envs/est/bin/python - (active v5 builder 및 v4 원문 정적 확인): passed
git diff --check: passed
초기 실행은 기본 Python의 openai 및 est 환경의 PyJWT/MCP 누락으로 import 실패했다. 해당 의존성은 /tmp/pr156-test-deps에 설치해 재실행했다.
```

## 6. 발견한 문제 / 남은 리스크

- 과거 v4 템플릿 내부의 문장 중복은 재현성 보존을 위해 남아 있다.

## 미확인 사항

- Prompt 본문을 변경한 뒤의 실제 모델 품질은 평가하지 않았다. 이번 변경은 Prompt 본문을 변경하지 않았다.

## 7. 다음 작업

- 후속 PR의 CI 결과를 확인한다.
