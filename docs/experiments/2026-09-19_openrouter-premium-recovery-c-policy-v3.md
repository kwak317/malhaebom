# OpenRouter Premium recovery — C policy v3

## 목적

2026-09-19 Basic 전체 평가에서 DeepSeek V4.1 Flash와 Gemini 3.8 Flash가 자동 품질 기준에 실패한
case만 대상으로 Premium 모델의 복구 성능과 추가 비용·지연을 확인한다. Qwen 실패는 모집단에서 제외한다.

## 환경과 입력

- 브랜치: `feat/llm-evaluation-foundation`, 미커밋 변경 상태
- Python: 프로젝트 로컬 `.venv-llm-eval` Python 3.12.3
- dataset: `evals/dataset.v2.jsonl`
- prompt label: `coaching-output-v3`
- policy: `independent-intent-observed-result-context-v3`
- grader: `labels-support-evidence-semantic-critical-v4`
- strict JSON Schema, `provider.require_parameters=true`, 자동 routing
- temperature/reasoning: 모델 기본값, SDK retry 0
- source Basic: DeepSeek 7 failures, Gemini 5 failures
- 고유 failure set: 8건(10, 13, 16, 17, 19, 20, 21, 22)
- case 20: known ambiguous로 별도 포함/제외 집계
- Premium: DeepSeek V4 Pro, Claude Sonnet 5, GPT-5.6 Terra

실행 명령:

```bash
.venv-llm-eval/bin/python -B \
  local-results/openrouter-premium-recovery-c-policy-20260919/execute.py --live
```

## 결과

정식 측정은 3종×8건=24건이며 API 인프라 실패와 retry는 없다. semantic 사람 점수는 전부 null이다.

| Premium | 계약 | 전체 복구 | case20 제외 | DeepSeek 실패 복구 | Gemini 실패 복구 | 측정 비용 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek V4 Pro | 6/8 | 2/8 | 2/7 | 2/7 | 0/5 | $0.094106798864 |
| Claude Sonnet 5 | 8/8 | 2/8 | 2/7 | 2/7 | 0/5 | $0.521664 |
| GPT-5.6 Terra | 8/8 | 4/8 | 4/7 | 4/7 | 1/5 | $0.0636197 |

case 20은 세 Premium 모두 복구하지 못했다. 측정 24건 비용 합계는 $0.679390498864다.
다만 첫 실행의 저장 순서 오류로 case13의 Premium 3회 응답이 파일에 보존되지 않았다. 이들은
instrumentation failure로 품질·복구 분모에서 제외했고, provider/token/cost를 알 수 없어 실제 총 청구액은 확정할 수 없다.
오류 수정 후 정식 24건을 다시 측정했으며 이 사실과 측정 불가 호출을 별도 JSON에 보존했다.

## 해석 범위

- failure type 복구는 source Basic 두 모델의 실패 유형을 case ID로 중복 제거해 계산했다.
- Basic→Premium 비용은 각 Basic 모델이 실제 실패한 case에만 해당 Premium을 호출하는 fallback으로 계산했다.
- case20 포함/제외 결과를 모두 제공한다.
- 자동 품질 복구는 사람 semantic 품질이나 실제 사용자 만족도를 뜻하지 않는다.
- 상세 raw·usage·provider·generation·latency 및 보고서는
  `local-results/openrouter-premium-recovery-c-policy-20260919/`에 있다.
