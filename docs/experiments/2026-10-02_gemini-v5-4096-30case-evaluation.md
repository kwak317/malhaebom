# Gemini v5 4,096-token 30건 출력 계약 재검증

## 목적

`coaching-v5-skill-owned`의 Gemini 실제 30건 평가에서 2,048-token 상한으로 발생한 JSON 절단 1건을 분리 확인한다. Prompt·Skill·평가셋은 유지하고 최대 출력만 4,096 tokens로 올린다.

## 실행 조건

- 모델: OpenRouter `google/gemini-3.5-flash-lite`
- 평가셋: `evals/dataset.v2.jsonl` 합성 30건, repeat 1회
- Prompt: `coaching-v5-skill-owned` (`c4194d1a...`)
- Skill: `interview-coach-v6.1-domain-rules` (`problem-solving-v4-draft.3`)
- 최대 출력 / timeout: 4,096 tokens / 60초
- 원본 산출물: `local-results/gemini-v5-4096-live-30/` (Git 제외)

## 결과

| 항목 | 결과 |
| --- | ---: |
| 계약 준수율 | 100.0% (30/30) |
| 규칙 기반 정확도 | 92.6% |
| Label 정확도 | 0.9083 |
| Evidence 정확도 | 0.9493 |
| ID 정확도 | 1.0 |
| 알려진 비용 | USD 0.171308 |
| 비용 미확인 호출 | 0 |
| p50 / p95 지연 | 4393.2ms / 6166.8ms |
| 실패 | 없음 |
| provider 종료 사유 | `stop` 30건 |

## 해석과 한계

- 2,048-token 실행의 `coach-failure-26` JSON 절단은 이번 4,096-token 실행에서 재현되지 않았다.
- 이 측정은 Prompt·Skill·모델·평가셋을 고정했지만 출력 상한과 timeout이 달라, 이전 v4/v5 비교의 비용·지연·품질 우열을 대체하지 않는다.
- 자동 의미 판정/근거 불일치가 남은 사례는 `coach-normal-09`, `coach-boundary-13`, `coach-boundary-16`, `coach-boundary-17`, `coach-boundary-19`, `coach-boundary-20`, `coach-failure-27`이다. 사람 semantic 검토는 아직 없다.
- 계약 30/30은 합성 평가 runner의 출력 계약 증거이며, 실제 로그인 사용자 운영 E2E나 출시 품질 증거가 아니다.
