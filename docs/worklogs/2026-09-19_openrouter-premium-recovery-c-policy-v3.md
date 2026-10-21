# Worklog — Premium recovery 평가

- 일시: 2026-09-19
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/specs/coaching-evaluation-ops.md`, C policy v3

## 1. 목적

DeepSeek/Gemini Basic 품질 실패를 case 기준으로 중복 제거하고 Premium 3종의 복구율·비용·지연을
현재 정책으로 측정한다. Qwen은 제외하고 case20 포함/제외 결과를 모두 제공한다.

## 2. 작업 전 상태

Basic 전체 평가에서 DeepSeek는 7건, Gemini는 5건 실패했고 합집합은 8건이었다.
기존 Basic 원본과 Qwen 결과는 보존된 상태였다.

## 3. 수행 내용

- source Basic 실패와 유형·execution ID를 `failure-set.json`에 고정했다.
- prompt label `coaching-output-v3`, strict schema, 자동 routing, 모델 기본 reasoning 조건으로 실행했다.
- Premium별 고유 8case를 한 번씩 측정하고 raw/provider/generation/usage.cost/token/latency를 저장했다.
- source Basic별, failure type별, case20 포함/제외 recovery와 fallback 최종 성공률·비용을 집계했다.
- 기존 Basic 결과·source hash·semantic null·Qwen 제외를 오프라인 검증했다.

## 주요 판단과 이유

같은 case가 양쪽 Basic에서 실패해도 Premium 출력은 한 번만 생성하고 양쪽 부모 execution ID를 연결했다.
case20은 expected C가 known ambiguous이므로 결과를 제거하지 않고 포함/제외 두 관점으로 제시했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `local-results/openrouter-premium-recovery-c-policy-20260919/` | 실행기, raw 24건, 집계, 검증 및 incident 기록 |
| `docs/experiments/2026-09-19_openrouter-premium-recovery-c-policy-v3.md` | 재현 조건과 결과 |
| `docs/CURRENT_STATE.md` | 현재 평가 결과 반영 |
| `evals/README.md` | Premium recovery 결과와 범위 기록 |

## 5. 검증

```text
24 unique measured executions / 8 unique failure cases
Qwen excluded, retry 0, prompt coaching-output-v3
source hashes unchanged, prior Basic result hashes unchanged
semantic scores null, generation/provider/usage.cost present 24/24
API infrastructure failures 0
```

전체 복구는 DeepSeek Pro2/8, Claude2/8, GPT Terra4/8이고 case20 제외 시 2/7, 2/7, 4/7이다.
정식 측정 비용 합계는 $0.679390498864다.

## 6. 발견한 문제 / 남은 리스크

첫 실행에서 응답 저장 전 `classification`을 참조해 case13 Premium3종의 응답·usage가 보존되지 않았다.
이를 `instrumentation-failures.json`에 기록하고 분류 초기화 순서를 수정한 후 정식24건을 측정했다.
측정 불가 3회의 실제 비용은 알 수 없으므로 캠페인의 총 청구 비용은 확정할 수 없다.

## 미확인 사항

- 사람 semantic 평가는 전부 null이다.
- 초기 instrumentation failure 3회의 provider/token/cost/generation ID는 미확인이다.
- case20 expected C의 독립 검토는 완료되지 않았다.

## 7. 다음 작업

- 사람 semantic 검토와 case20 정답 독립 검토 후 모델 선택 근거를 확정한다.
