# Gemini v5 Prompt 30건 평가

## 실행 조건

- 모델: `google/gemini-3.5-flash-lite` via OpenRouter
- 평가셋: `evals/dataset.v2.jsonl` 30건, repeat 1회
- Prompt: `coaching-v5-skill-owned`
- Skill: `interview-coach-v6.1-domain-rules`
- 최대 출력: 2,048 tokens, timeout 60초
- 원본 결과: `local-results/gemini-v5-live-30/` (Git 제외)

## 결과

| 항목 | 결과 |
| --- | ---: |
| 계약 준수율 | 96.7% (29/30) |
| 전체 규칙 기반 정확도 | 88.6% |
| 유효 응답 기준 정확도 | 91.6% |
| Label 정확도 | 0.8879 |
| Evidence 정확도 | 0.9638 |
| ID 정확도 | 1.0 |
| 알려진 비용 | USD 0.174643 |
| p50 / p95 지연 | 4429.6ms / 7215.8ms |

## 실패와 해석

- `coach-failure-26` 한 건은 2,032 completion tokens에서 JSON을 닫기 전에 종료됐다.
- 원본 `raw_output`이 중간 문자열에서 끝났고, 이는 2,048 token 상한에 의한 출력 절단으로 해석한다.
- 당시 격리 평가기는 자식의 `JSONDecodeError`를 `provider_error`로 표기했다. 후속 수정은 이를 `schema_violation`으로 분류하고 `finish_reason`을 attempt 기록에 보존한다.
- 이 결과는 구조화 출력 스키마가 29건에서 통과함을 보이지만, 30/30 계약 준수 증거는 아니다. 출력 한도를 4,096으로 높인 별도 30건 재실행이 필요하다.

## 의미 판정 불일치

유효 응답 중 label 또는 evidence가 기대값과 완전히 일치하지 않은 사례는 `coach-normal-09`, `coach-boundary-13`, `coach-boundary-16`, `coach-boundary-17`, `coach-boundary-19`, `coach-boundary-20`, `coach-failure-27`, `coach-failure-30`이다. 자동 평가는 인용·ID 계약은 높게 통과했지만, 이 사례들은 사람 검토로 의미 판정의 적절성을 확인해야 한다.
