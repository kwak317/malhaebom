# OpenRouter 모델 계열 다양성 평가

## 목적과 범위

최고 성능 모델 선정이 아니라 수업용 OpenRouter key로 접근 가능한 서로 다른 개발사 모델이 말해봄의 고정 코칭 계약을 얼마나 지원하는지 확인했다. 기존 `dataset.v2.jsonl` 30건, Skill bundle, `coaching-output-v3`, strict JSON Schema, 자동 provider routing, 모델 기본 temperature/reasoning, grader/policy를 유지했다. 사람 semantic 평가는 수행하지 않았다.

## 환경과 재현

- 실행일: 2026-09-21 (Asia/Seoul)
- branch/실행 코드: `feat/llm-evaluation-foundation`, 미커밋 `evals/run_openrouter_diversity.py`
- Python: 프로젝트 `.venv-llm-eval` Python 3.12
- dataset: `evals/dataset.v2.jsonl`, 30건
- preflight: case 01/16/23 (normal/boundary/failure)
- timeout 60초, SDK retry 0, orchestration retry 1, exponential backoff 2초
- 결과: `local-results/openrouter-diversity-20260921-v2/` (Git 제외)

```bash
.venv-llm-eval/bin/python -B evals/run_openrouter_diversity.py --stage discover \
  --output-dir local-results/openrouter-diversity-20260921-v2 \
  --max-models 30 --per-developer 2 --max-output-price 20
.venv-llm-eval/bin/python -B evals/run_openrouter_diversity.py --stage preflight \
  --output-dir local-results/openrouter-diversity-20260921-v2 \
  --max-models 30 --per-developer 2 --max-output-price 20 \
  --timeout-seconds 60 --retries 1 --backoff-seconds 2 --concurrency 4
.venv-llm-eval/bin/python -B evals/run_openrouter_diversity.py --stage full \
  --output-dir local-results/openrouter-diversity-20260921-v2 \
  --max-models 30 --per-developer 2 --max-output-price 20 \
  --timeout-seconds 60 --retries 1 --backoff-seconds 2 --concurrency 10
```

## Discovery와 preflight

인증된 OpenRouter `/models/user`에서 283개를 발견했다. text 입력/text 단독 출력, `response_format` 지원, 명백한 router/batch alias 제외 후 214개가 eligible이었다. 가격 상한과 개발사 round-robin으로 30개 개발사에서 1개씩 선택했다. Cohere는 목록에 있었지만 structured output 조건을 만족하는 후보가 없어 선택되지 않았다.

30개×3건 preflight 결과는 PASS 15, CONTRACT_VIOLATION 6, MODEL_UNAVAILABLE 4, API_ERROR 4, RATE_LIMITED 1이다. 접근/실행 실패도 삭제하지 않고 최종 JSON/CSV/Markdown에 보존했다. 알려진 preflight 비용은 $0.781658884이며 비용 미확인 호출은 40개였다.

## 30건 본평가 결과

PASS 15개를 모두 30건씩 실행해 450개 고유 사례를 저장했다. 15개 모델 모두 30건 완료했다. preflight와 본평가 전체의 알려진 비용 합계는 $8.2166702564이며 비용 미확인 호출은 67개다. 이는 `usage.cost`가 있는 호출만 합산한 값이다.

| Model | 계약 성공/30 | 계약 위반 | p50 ms | p95 ms | 알려진 비용 USD |
|---|---:|---:|---:|---:|---:|
| anthropic/claude-sonnet-5 | 29 | 1 | 28,731 | 60,976 | 1.933426 |
| google/gemini-3.8-flash | 30 | 0 | 13,248 | 21,687 | 0.379329 |
| meta/muse-glimmer-30b | 20 | 10 | 44,138 | 234,516 | 0.138146 |
| qwen/qwen3.8-27b | 29 | 1 | 107,371 | 407,505 | 0.498622 |
| ~deepseek/deepseek-pro-latest | 29 | 1 | 36,163 | 70,530 | 0.328725 |
| mistralai/mistral-medium-3-5 | 16 | 1 | 6,935 | 7,901 | 0.270902 |
| x-ai/grok-4.6 | 30 | 0 | 50,036 | 68,586 | 0.939494 |
| nvidia/nemotron-3.5-lightning | 20 | 10 | 7,877 | 315,690 | 0.023360 |
| anthracite-org/magnum-v4-72b | 14 | 16 | 49,929 | 72,887 | 0.631433 |
| bytedance-seed/seed-2-1-turbo | 28 | 2 | 144,847 | 339,371 | 0.934968 |
| inception/mercury-2.5 | 18 | 12 | 6,603 | 8,582 | 0.023647 |
| inclusionai/ling-3.0-flash-vl | 26 | 4 | 46,005 | 92,291 | 0.020550 |
| minimax/minimax-m3 | 26 | 4 | 31,457 | 147,031 | 0.048474 |
| moonshotai/kimi-k3 | 30 | 0 | 37,730 | 100,763 | 1.837710 |
| xiaomi/mimo-v2.5-pro | 26 | 4 | 61,574 | 109,578 | 0.178719 |

Mistral은 13건 rate limit이 추가되어 계약 성공이 16건이다. latency는 최종 호출 기록 기준이며 일부 OpenRouter/provider 응답이 SDK timeout 설정보다 길게 관찰됐다. 실제 routed provider는 모델별 summary에 별도 보존했다.

### Preflight 탈락 보존

| 결과 | 모델 |
|---|---|
| CONTRACT_VIOLATION | `~openai/gpt-terra-latest`, `microsoft/phi-4`, `ibm-granite/granite-4.2-8b`, `inference-net/schematron-v2-turbo`, `sao10k/l3.3-euryale-70b`, `upstage/solar-pro4` |
| MODEL_UNAVAILABLE | `cognitivecomputations/dolphin-mistral-24b-venice-edition`, `mancer/weaver`, `nousresearch/hermes-4-405b`, `z-ai/glm-5.3-flashx` |
| API_ERROR | `gryphe/mythomax-l2-13b`, `morph/morph-v3-large`, `tencent/hy4-preview`, `undi95/remm-slerp-l2-13b` |
| RATE_LIMITED | `thedrummer/cydonia-24b-v4.1` |
| POLICY_RESTRICTED | 없음 |

## Diversity follow-up

1차에 포함되지 않은 지정 10개 모델을 같은 discovery metadata와 3-case preflight로 평가했다.
기존 결과는 재호출하지 않았고 별도 `local-results/openrouter-diversity-followup-20260921/`에 보존했다.

| 모델 | Preflight / 본평가 |
|---|---:|
| `~openai/gpt-luna-latest` | PASS, 25/30 |
| `~anthropic/claude-haiku-latest` | PASS, 27/30 |
| `google/gemini-3.5-flash-lite` | PASS, 30/30 |
| `meta-llama/llama-4-maverick` | PASS, 25/30 |
| `qwen/qwen3.6-35b-a3b` | PASS, 28/30 |
| `~deepseek/deepseek-flash-latest` | PASS, 26/30 |
| `mistralai/mistral-small-2603` | RATE_LIMITED, 본평가 없음 |
| `nvidia/nemotron-3-super-120b-a12b` | CONTRACT_VIOLATION, 본평가 없음 |
| `microsoft/wizardlm-2-8x22b` | MODEL_UNAVAILABLE, 본평가 없음 |
| `~x-ai/grok-latest` | PASS, 30/30 |

Follow-up 알려진 비용은 $2.0592654581, 비용 미확인 호출은 13개다. 1차와 합친 누적은
preflight 40개, PASS 22개, 30건 본평가 모델 22개(660건), 알려진 비용 $10.2759357145,
비용 미확인 호출 80개다. 누적 수치는 `combined-summary.json`과 두 실행의 `summary.json`을 대조했다.
이 단계에서도 semantic 평가는 수행하지 않았다.

### Follow-up 재현

기존 1차 output directory를 재사용하지 않고, `--max-models 0`과 명시적 `--model` 10개로
discover/preflight/full을 같은 새 directory에서 실행한다. 정확한 모델 목록은 이 표와 실행 manifest를
따르며, 완료된 호출은 atomic JSON을 재사용한다.

## 한계

- preflight 3건 통과는 전체 30건 계약 통과를 보장하지 않았다.
- 모델별 사람 semantic 검토가 없으므로 semantic 결과는 null이며 계약 성공을 코칭 품질로 해석하지 않는다.
- 자동 routing 때문에 같은 model id가 여러 실제 provider로 분산될 수 있다.
- 비용 미확인 호출 67개가 있어 $8.2166702564는 하한 성격의 알려진 합계다.
- discovery는 2026-09-21 현재 키의 provider/privacy/guardrail 설정에 종속된다.
- 40개 diversity 누적 계약 결과는 폭넓은 호환성 탐색이며 최종 모델 semantic 순위가 아니다.

후속 후보 판단은 [Decision log](../DECISIONS.md), 재현 명령은 [평가 가이드](../../evals/README.md)를 따른다.
