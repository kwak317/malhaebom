# Gemini 구조화 출력 재평가

## 목적

Gemini/OpenRouter 평가 runner가 `json_object`만 요청해 발생한 구조화 출력 계약 위반을 수정한 뒤, 동일한 합성 30건 평가셋에서 실제 모델 응답을 재검증한다.

## 실행 조건

- 모델: `google/gemini-3.5-flash-lite`
- 평가셋: `evals/dataset.v2.jsonl` 30건
- Prompt: `coaching-user-supplied-v4-verification`
- Skill: `interview-coach-v6`
- 기준: `problem-solving-v4-draft.3`
- 실행 결과 경로: `local-results/gemini-live-30-intent-fixed/` (Git 제외)

이번 결과에는 위 v4 Prompt의 당시 원문이 적용됐다. 이후 기본 Prompt는 `coaching-v5-skill-owned`로 변경됐다. v4의 intent 설명 중 겹치는 문장은 평가 입력 재현을 위해 당시 버전 그대로 보존한다.

## 결과

| 항목 | 결과 |
| --- | ---: |
| 계약 준수율 | 100.0% |
| 규칙 기반 정확도 | 93.7% |
| Label 정확도 | 0.925 |
| Evidence 정확도 | 0.9565 |
| ID 정확도 | 1.0 |
| 알려진 비용 | USD 0.186445 |
| p50 지연 | 4360.9ms |
| p95 지연 | 4790.4ms |
| schema/provider 실패 | 0건 |

## 해석

구조화 출력 계약, 근거 ID 참조, provider 호출은 30건 모두 통과했다. 따라서 이전 실행의 `schema_violation` 28건과 `provider_error` 2건은 재현되지 않았다.

의미 판정 또는 근거 선택이 기대값과 완전히 일치하지 않은 사례는 7건(`coach-normal-01`, `coach-boundary-13`, `coach-boundary-16`, `coach-boundary-17`, `coach-boundary-19`, `coach-failure-27`, `coach-failure-30`)이다. 특히 `coach-normal-01`은 결과 확인이 없다는 이유만으로 intent를 `partial`로 낮추는 비결정적 응답이 다시 나타났다. Prompt의 intent/criterion 분리 규칙을 강화했지만, 이 한 번의 30건 실행만으로 의미 품질 목표 달성을 단정하지 않는다.

## 결론

이 변경은 실제 모델의 출력 계약 실패를 해결했다. 의미 품질은 동일 평가셋 반복 실행 및 사람 검토를 통해 추가 확인해야 한다. 원본 응답과 provider metadata가 들어 있는 `comparison.json`은 Git에 커밋하지 않는다.
