# Gemini structured output 계약 수정 Worklog

## 목적

실제 Gemini 30건 평가에서 발생한 `schema_violation` 28건과 provider 오류 2건 중, 평가 runner가 Gemini에 서비스 출력 스키마를 요청하지 않는 문제를 수정한다.

## 작업 전 상태

- `local-results/llm-live-30/comparison.md`에서 Gemini 계약 준수율 0%를 확인했다.
- 실제 응답은 JSON 파싱에는 성공했지만 `job_alignment`이 배열이 아닌 객체로 반환되는 등 `CoachingLLMOutput` 스키마를 지키지 않았다.
- `evals/run_model_comparison.py`는 Ollama와 일부 GPT 모델에만 JSON Schema를 요청하고 Gemini/OpenRouter 후보에는 `json_object`만 요청했다.

## 변경 내용

- 모든 OpenAI-compatible 후보에 `CoachingLLMOutput` JSON Schema를 요청하도록 runner를 수정했다.
- OpenRouter Gemini 후보가 strict schema 요청을 사용하는 회귀 테스트를 추가했다.
- 실제 Gemini preflight에서 결과 확인 누락으로 `intent_assessment=partial`을 반환한 사례를 기준으로, intent는 질문 관련성만 판단하고 기준별 누락은 해당 criterion에만 반영하도록 영문 Prompt 규칙과 회귀 테스트를 추가했다.
- `main` 병합 뒤 원격 브랜치에 남은 중복 조건문과 닫히지 않은 테스트 괄호를 복구했다. 이 훼손은 `c16b413`의 정상 형식과 비교해 확인했으며, 각각 `evals/run_model_comparison.py`와 `backend/tests/test_coaching_eval.py`의 import를 막고 있었다.
- 현재 기본 Prompt는 `coaching-v5-skill-owned`임을 확인했다. 도메인 판정 규칙은 `skills/interview-coach/SKILL.md`가 소유하고, 기본 Prompt는 운영·출력 계약만 소유한다. 회귀 테스트도 이 실제 기본 경로를 검증하도록 갱신했다.

## 변경 파일

- `evals/run_model_comparison.py`
- `backend/tests/test_coaching_eval.py`
- `prompts/coaching-user-supplied-v4-verification.md`
- `backend/tests/test_coaching_prompt.py`
- `docs/worklogs/2026-10-02_0935_gemini-structured-output-fix.md`

## 검증

- schema-format 및 기본 Prompt 경계 targeted tests: 11개 통과
- coaching test suite: 110개 통과
- `git diff --check`: 통과
- 수정 후 Gemini 1건 preflight: 계약·정확도·Label·Evidence·ID 모두 100%, 실패 0건
- 수정 후 Gemini 30건: 계약 준수율 100%, 정확도 93.7%, Label 0.925, Evidence 0.9565, ID 1.0, schema/provider 실패 0건, p50 4360.9ms, p95 4790.4ms, 알려진 비용 USD 0.186445

## 미해결 사항

- 이전 `provider_error` 2건은 수정 후 30건 실행에서 재현되지 않았다.
- 7개 사례의 의미 판정 또는 근거 선택이 기대값과 완전히 일치하지 않았다. 특히 `coach-normal-01`의 intent 판정은 같은 입력에서 비결정적으로 `partial`이 될 수 있어 추가 반복 평가와 사람 검토가 필요하다.

## 다음 작업

1. 동일 평가셋 반복 실행과 사람 검토로 7개 불일치 사례를 점검한다.
2. 다른 팀원에게 PR #156 리뷰를 요청한다.
