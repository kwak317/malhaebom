# Worklog — LM Studio JSON Schema 평가 호환

- 일시: 2026-09-18 15:48
- 작업자/에이전트: Codex
- 관련 이슈/PR: PR 생성 전
- 관련 요구사항/결정: `docs/specs/coaching-evaluation-ops.md` AC-08, `docs/REQUIREMENTS.md` 모델 비교와 structured output 계약 준수율

## 1. 목적

LM Studio OpenAI-compatible 서버가 `response_format.type=json_object` 요청을 HTTP 400으로 거부해 로컬 EEVE 평가 30건이 모두 provider 오류가 된 문제를 고친다.

## 2. 작업 전 상태

- `evals/run_model_comparison.py`는 모든 OpenAI-compatible 후보에 `{"type": "json_object"}`를 요청했다.
- 사용자가 LM Studio에서 `andreass123/EEVE-Korean-Instruct-2.8B-v1.0-Q4_K_M-GGUF`를 실행한 결과, 30건 모두 `BadRequestError: 400 - 'response_format.type' must be 'json_schema' or 'text'`로 실패했다.
- 원래 작업 폴더의 `max_completion_tokens=2048` 미커밋 변경은 사용자 작업으로 분리했으며 이 브랜치에 포함하지 않았다.

## 3. 수행 내용

- 평가 runner가 `CoachingLLMOutput.model_json_schema()`를 strict `json_schema` OpenAI-compatible 요청으로 감싸도록 변경했다.
- LM Studio 호환 요청의 type, 이름, strict 설정, 최상위 object schema를 검증하는 회귀 테스트를 추가했다.
- 평가 README에 provider의 JSON Schema 지원 조건을 기록했다.

## 주요 판단과 이유

LM Studio의 HTTP 400은 모델 응답 전에 발생한 서버 요청 형식 불일치였다. 단순 text 모드로 완화하지 않고 기존 런타임 provider와 같은 strict JSON Schema 계약을 사용해, 실제 모델 비교에서도 출력 형식 강제와 후속 서버 검증을 유지한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/run_model_comparison.py` | strict coaching JSON Schema 요청 생성 및 사용 |
| `backend/tests/test_coaching_eval.py` | OpenAI-compatible runner 요청 형식 회귀 테스트 |
| `evals/README.md` | JSON Schema provider 호환 조건 문서화 |
| `docs/worklogs/2026-09-18_1548_lm-studio-json-schema.md` | 작업 근거와 검증 결과 기록 |

## 5. 검증

```text
C:\Users\home\AppData\Local\Programs\Python\Python311\python.exe -m unittest backend.tests.test_coaching_eval
Ran 5 tests in 0.016s
OK

C:\Users\home\AppData\Local\Programs\Python\Python311\python.exe -m unittest backend.tests.test_coaching_runtime
ModuleNotFoundError: No module named 'fastapi'
```

## 6. 발견한 문제 / 남은 리스크

- LM Studio 실제 모델 재실행은 이 작업공간에서 수행하지 않았다. PR 반영 후 LM Studio에서 30건 비교를 재실행해 결과를 별도 기록해야 한다.
- JSON Schema 강제는 형식만 보장하며, 근거·기준 판정 품질은 기존 서버 검증과 평가 점수로 별도 측정한다.

## 미확인 사항

- 이 Python 3.11 작업공간에는 FastAPI가 없어 `backend.tests.test_coaching_runtime` 전체 수집을 실행하지 못했다.
- 실제 provider별 strict JSON Schema 지원 범위와 model별 품질은 별도 실행 전까지 확인하지 않았다.

## 7. 다음 작업

- LM Studio에서 Qwen2.5-7B-Instruct 또는 EEVE GGUF를 대상으로 30건 평가를 재실행한다.
- 생성된 `local-results/`의 계약 준수율, 정확도, 지연과 실패 원인을 `EVAL_REPORT.md`에 근거와 함께 기록한다.
