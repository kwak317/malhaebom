# 로컬 Ollama 모델 평가 Spec

## Why

- **페르소나**: 말해봄의 코칭 LLM 후보를 선정하는 개발 팀원.
- **상황**: 동일한 합성 코칭 평가셋으로 로컬 SLM과 API 모델을 비교해야 한다.
- **문제**: 기존 runner가 Ollama가 허용하지 않는 `json_object` 형식을 보내고, 전체 30건 이전에 한 건으로 연결·계약을 확인할 수 없다.
- **측정 지표**: Qwen3·EEVE 각각의 사전 점검 결과와 30건 계약 준수율·정확도·p50/p95를 동일 결과 형식으로 보관한다.

## Goal

- Ollama 후보가 JSON Schema 응답 형식을 사용해 기존 서버 계약 검증까지 도달하게 한다.
- `--case-id`로 고정 평가셋 한 건을 사전 점검하고, `--max-completion-tokens`로 출력 상한을 실행별로 고정한다.
- **Out of Scope**: 별도 Gemini direct API adapter 추가, 평가셋·정답 변경, 재시도 정책, 운영 API 연결.

## What

### Happy Path

1. 실행자가 Ollama endpoint와 후보 모델 ID, `--case-id`, 출력 상한을 지정한다.
2. runner가 지정 case 한 건에 JSON Schema를 요청한다.
3. 기존 Pydantic·ID·인용 검증과 규칙 기반 채점을 수행해 JSON/Markdown 결과를 저장한다.
4. 사전 점검 성공 후 같은 후보·상한으로 30건 평가를 실행한다.

### Edge Cases

| 상황 | 처리 |
| --- | --- |
| 알 수 없는 case ID | 외부 호출 전 명확한 CLI 오류로 종료 |
| Ollama가 JSON Schema를 거부 | 해당 요청을 `provider_error`로 기록 |
| 모델이 JSON이나 계약을 위반 | `schema_violation`으로 기록 |
| 출력 상한이 1 미만 | 외부 호출 전 CLI 오류로 종료 |
| 모델 미설치·endpoint 미응답 | `provider_error`로 기록 |

## How

- 변경 대상은 `evals/run_model_comparison.py`와 `backend/tests/test_coaching_eval.py`다.
- 후보 provider 값에 `ollama`를 추가한다. OpenAI-compatible provider는 기존 동작을 유지한다.
- Ollama 요청은 OpenAI-compatible endpoint의 `response_format.type=json_schema`와 `CoachingLLMOutput.model_json_schema()`를 사용한다.
- OpenAI GPT-5 후보는 strict JSON Schema로 정규화하고 `reasoning_effort=minimal`을 요청한다.
- CLI 기본 `--max-completion-tokens`는 2048이며 로컬 실행은 768을 명시한다.
- `--case-id` 지정 시 선택 case만 실행하며, 결과 메타데이터에 실행 case 수가 남는다.

## AC

- **AC-01**: GIVEN 유효한 case ID WHEN `--case-id`로 선택 THEN runner는 해당 case 한 건만 실행한다.
- **AC-02**: GIVEN 존재하지 않는 case ID WHEN 실행 THEN provider 호출 전에 오류로 종료한다.
- **AC-03**: GIVEN Ollama 후보 WHEN 요청 생성 THEN `json_schema`와 코칭 출력 JSON Schema를 전달한다.
- **AC-04**: GIVEN 0 이하 출력 상한 WHEN 실행 THEN provider 호출 전에 오류로 종료한다.
- **AC-05**: GIVEN 기존 mock 후보 WHEN 새 옵션 없이 실행 THEN 기존 30건 runner 검증이 통과한다.
