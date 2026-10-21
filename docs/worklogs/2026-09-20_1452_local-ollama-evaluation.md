# 로컬 Ollama 모델 평가 사전 점검

- 일시: 2026-09-20 14:52 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/specs/local-ollama-model-evaluation.md`, 코칭 평가·관측 Spec AC-08

## 1. 목적

Ollama 로컬 후보가 기존 코칭 출력 계약을 지원하도록 runner를 보완하고, Qwen3 4B와 EEVE Korean 2.8B Q4를 전체 평가 전 한 건으로 점검한다.

## 2. 작업 전 상태

- runner는 OpenAI-compatible 후보만 지원했고 `json_object`를 사용했다.
- 기존 EEVE 실행은 Ollama의 JSON 출력 형식 거부로 HTTP 400, Qwen 실행은 모델 ID 404로 실패한 기록이 있었다.
- 현재 로컬에는 `qwen3:4b`만 설치되어 있었고 EEVE Q4는 없었다.

## 3. 수행 내용

1. `ollama` 후보 provider, `--case-id`, `--max-completion-tokens`를 추가했다.
2. Ollama 후보에는 `CoachingLLMOutput` Pydantic JSON Schema를 요청하도록 했다.
3. Qwen3 한 건 사전 점검을 실행했다.
4. EEVE Q4 1.8GB를 Ollama에 내려받고 동일 조건의 한 건 사전 점검을 실행했다.
5. 실행법과 현재 상태를 갱신했다.
6. OpenRouter의 GPT-5 mini/nano 사전 점검에서 확인한 strict schema 거부를 수정하고 재측정했다.
7. 사전 점검 후보 중 Gemini 3.5 Flash-Lite, GPT-5 mini, GPT-5.6 Terra를 동일 조건의 합성 30건으로 각 1회 비교했다.

## 주요 판단과 이유

- 사전 점검이 서버 계약을 통과하지 못한 후보는 30건 전체 실행을 하지 않았다. 실패 원인과 성능을 분리하고 불필요한 GPU 시간을 쓰지 않기 위해서다.
- `json_object`가 아니라 Ollama가 수용하는 `json_schema`를 사용했다. 단, JSON Schema 생성이 서버 의미 계약 통과를 보장하지는 않는다.
- OpenAI strict mode는 모든 object property를 `required`에 넣어야 하므로 Pydantic schema를 provider 호환 형식으로 정규화했다. nullable 필드는 기존 schema의 `null` 허용을 유지한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/run_model_comparison.py` | Ollama provider·사전 점검 case 선택·출력 토큰 상한·JSON Schema 요청 추가 |
| `backend/tests/test_coaching_eval.py` | Ollama schema와 case 선택 회귀 테스트 추가 |
| `evals/README.md` | 로컬 사전 점검 및 전체 평가 실행 절차 추가 |
| `docs/specs/local-ollama-model-evaluation.md` | 기능 범위와 AC 기록 |
| `docs/CURRENT_STATE.md` | 평가 runner, 사전 점검 및 API 30건 비교 상태 반영 |
| `EVAL_REPORT.md` | Git에 남길 수 있는 모델별 30건 요약·게이트 판정 기록 |

## 5. 검증

```text
C:\Users\home\Desktop\proj2-3\.venv\Scripts\python.exe -m unittest discover -s backend/tests
200 tests, OK

Qwen3 preflight (coach-normal-01, 768 tokens, 45s)
28,559.8ms, schema_violation: met/related 항목의 evidence 누락

EEVE preflight (coach-normal-01, 768 tokens, 45s)
28,111.4ms, schema_violation: non-met 항목의 needed 누락

GPT-5 mini strict preflight (coach-normal-01, 4096 tokens, 60s)
7,214.8ms, contract 100%, 규칙 기반 정확도 88.9%, $0.002726

GPT-5 nano strict preflight (coach-normal-01, 3072 tokens, 60s)
6,012.3ms, schema_violation: not_observed 항목에 evidence를 반환

API 30건 비교 (각 후보 1회, 4096 tokens, 60s)
Gemini 3.5 Flash-Lite: 계약 66.7%, 규칙 기반 정확도 45.8%, 총 $0.0571895, p50 2,536.2ms, p95 3,089.4ms, schema_violation 10건
GPT-5 mini: 계약 36.7%, 규칙 기반 정확도 20.4%, 총 $0.03212225, p50 7,281.7ms, p95 10,465.1ms, schema_violation 19건
GPT-5.6 Terra: 계약 96.7%, 규칙 기반 정확도 55.1%, 총 $0.445284, p50 6,172.1ms, p95 9,305.7ms, schema_violation 1건
```

## 6. 발견한 문제 / 남은 리스크

- Qwen3와 EEVE, GPT-5 nano는 요청·JSON 처리 단계에는 도달했지만 서버 의미 계약을 통과하지 못했다.
- 현재 p50/p95는 실패 요청도 포함하므로, 성공 요청 속도와 실패 지연을 분리하는 후속 개선이 필요하다.
- API 후보 3종 30건 비교에서는 Terra만 계약 준수율 95% draft 게이트를 통과했지만, 합성 입력·1회 실행·규칙 기반 정확도만으로 운영 모델을 확정할 수 없다.

## 미확인 사항

- EEVE 2K context window에서 전체 Skill·schema가 장기적으로 안정적인지 확인하지 않았다.
- 프롬프트 경량화 또는 모델별 repair/retry가 계약 준수율을 개선하는지는 평가하지 않았다.

## 7. 다음 작업

- 소형 모델용으로 출력 스키마·프롬프트 길이를 축소할 별도 범위를 결정한다.
- Terra의 단일 quote 불일치 원인을 분석하고, 별도 고유 입력 100건과 사람 검토로 재평가한다.
