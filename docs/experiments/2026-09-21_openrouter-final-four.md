# OpenRouter Final Four 동일 조건 비교

## 목적

초기 후보 심층 비교와 OpenRouter diversity 탐색 뒤 남은 네 모델을 같은 현재 dataset·prompt·schema와
생성 설정으로 새로 실행해 기계 평가 기준 1차 최종 후보를 좁힌다. Diversity 응답은 재사용하지 않았고,
사람 semantic 점수는 생성하지 않았다.

## 고정 조건과 재현 metadata

| 항목 | 값 |
|---|---|
| 실행 시각 | 2026-09-21T06:05:05.241152Z |
| Dataset | `evals/dataset.v2.jsonl`, 30건, SHA-256 `7259d1d0a92556c034f41a027a4a4fd230c6a199c7e616dd52d077e51cb5b9a9` |
| Skill | `interview-coach-v2`, bundle SHA-256 `dbd00a310941d2a552c1e89cf33bd9d652b5ad70d56527989f56aded5bf2cf7c` |
| Criteria | `problem-solving-v4-draft.1` |
| Prompt | `coaching-output-v3` |
| Schema 구현 | `backend/app/schemas/coaching.py`, SHA-256 `81d1d8d44daa963185184208e42b379d88d154d7b612c0917ccb51ff13eb732c` |
| API | `https://openrouter.ai/api/v1`, 자동 routing, `provider.require_parameters=true` |
| 생성 설정 | temperature/reasoning/max output 모두 model default |
| 재시도 | SDK 0, orchestration 1회, backoff 2초 |
| timeout/concurrency | 60초 / 8 |
| 로컬 결과 | `local-results/openrouter-final-four-20260921/` (Git 제외) |

모델 ID는 `google/gemini-3.5-flash-lite`, `google/gemini-3.8-flash`,
`openai/gpt-5.6-luna`, `openai/gpt-5.6-terra`다. 가격은 별도 고정표가 아니라 실행 응답의
`usage.cost`를 사용했다. 따라서 비용 미확인 호출은 0으로 간주하지 않는다.

## 기계 평가 결과

| 모델 | Contract | 위반/기타 실패 | p50 / p95 | Input / Output token | 알려진 총비용 | 확인 호출당 평균 |
|---|---:|---|---:|---:|---:|---:|
| Gemini 3.5 Flash Lite | 30/30 | 없음 | 3.41s / 4.20s | 197,477 / 21,077 | $0.10706534 | $0.00356884 |
| Gemini 3.8 Flash | 30/30 | 없음 | 12.60s / 21.28s | 197,477 / 53,659 | $0.34932900 | $0.01164430 |
| GPT-5.6 Luna | 29/30 | validator violation 1 | 9.36s / 13.77s | 186,154 / 26,277 | $0.03914948 | $0.00130498 |
| GPT-5.6 Terra | 10/30 | schema/integration 실패 20 | 1.18s / 8.29s | 61,893 / 6,340 | ≥$0.10570740 | 확인 10건 평균 $0.01057074 |

Terra 20건은 `raw_output=null`, `provider=null`, `ValueError`, usage 없음으로 보존됐다. 모델이 생성한
응답의 의미 품질 실패로 단정하지 않으며, Terra와 전체 알려진 비용 $0.60125122는 하한이다.

## 판단

기계 평가 기준 1차 최종 후보는 Gemini 3.5 Flash Lite와 GPT-5.6 Luna다.

- Flash Lite: 30/30 계약, 가장 낮은 p50/p95, Gemini 3.8 Flash보다 낮은 비용.
- Luna: 29/30 계약, 비용이 전부 확인된 세 모델 중 가장 낮은 30건 비용.
- Gemini 3.8 Flash: 계약은 30/30이나 Flash Lite 대비 비용·지연이 높고 semantic 추가 이점 미확인.
- Terra: 과거 failure subset fallback 결과는 좋았으나 이번 OpenRouter 경로의 integration/schema
  실패가 많아 안정적인 기본 후보에서 제외.

이 판단은 production 모델 확정이 아니다. 아래 blind 사람 평가 결과에 따라 바뀔 수 있다.

## 실행 재현

먼저 diversity discovery 결과를 준비한다. catalog에는 네 모델의 eligible metadata가 있어야 한다.
`--live`가 없으면 계획만 출력하고 API를 호출하지 않는다.

```bash
.venv-llm-eval/bin/python -B evals/run_openrouter_final_four.py \
  --catalog local-results/openrouter-diversity-20260921-v2/discovery.json \
  --output-dir local-results/openrouter-final-four-reproduction

.venv-llm-eval/bin/python -B evals/run_openrouter_final_four.py --live \
  --catalog local-results/openrouter-diversity-20260921-v2/discovery.json \
  --output-dir local-results/openrouter-final-four-reproduction \
  --timeout-seconds 60 --retries 1 --backoff-seconds 2 --concurrency 8
```

API key는 루트 `.env` 또는 환경의 `OPENROUTER_API_KEY`만 사용하며 값은 출력·결과에 저장하지 않는다.

## Semantic blind 평가 재현

```bash
.venv-llm-eval/bin/python -B evals/build_final_four_semantic_review.py \
  --results-dir local-results/openrouter-final-four-reproduction

.venv-llm-eval/bin/python -B evals/aggregate_final_four_semantic.py \
  --review-csv local-results/openrouter-final-four-reproduction/semantic-blind-review.csv \
  --mapping local-results/openrouter-final-four-reproduction/semantic-blind-mapping.json \
  --output local-results/openrouter-final-four-reproduction/semantic-summary.json
```

후속 후보 판단은 [Decision log](../DECISIONS.md), 재현 명령의 canonical 설명은 [평가 가이드](../../evals/README.md)를 따른다.

CSV는 30case×4응답=120행이며 `core_15=Y` 60행만 먼저 평가할 수 있다. intent, evidence, needed,
코칭 유용성, grounding, 서비스 사용 가능성을 각각 1~5점으로 입력하고 comment를 남긴다. mapping은
검토 완료 전 reviewer와 분리한다. 빈 점수는 집계에서 제외하며 일부 항목만 채운 행은 오류로 차단한다.
