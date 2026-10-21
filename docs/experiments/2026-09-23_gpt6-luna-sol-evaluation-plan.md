# GPT-6 Luna / Sol 후보 비교 실행 계획

- 날짜: 2026-09-23
- 상태: strict-schema runner 보완 완료, provider 사용 한도로 추가 실호출 중단
- 브랜치: `experiment/gpt6-luna-sol-evaluation`
- 실행 진입점: `evals/run_gpt6_luna_sol_comparison.py`
- canonical 평가기: `evals/run_model_comparison.py`
- 관련 Worklog: [2026-09-23 GPT-6 평가 준비](../worklogs/2026-09-23_1130_gpt6-evaluation-prep.md)

## 목적

현재 서비스 기준 모델인 Gemini 3.5 Flash Lite와 새 OpenRouter 후보 GPT-6 Luna, GPT-6 Sol을
같은 Dataset, Prompt, Skill, 출력 계약, repair 정책으로 비교한다. Prompt 개선 실험과 모델
비교를 섞지 않고 **모델만 독립 변수**로 둔다.

OpenRouter 모델 ID는 2026-09-23 확인 기준 다음과 같다.

- `google/gemini-3.5-flash-lite`
- `openai/gpt-6-luna`
- `openai/gpt-6-sol`

GPT-6 참고:
- https://openrouter.ai/openai/gpt-6-luna
- https://openrouter.ai/openai/gpt-6-sol

가격은 문서의 고정값으로 판정하지 않고 OpenRouter 응답의 `usage.cost`를 canonical로 사용한다.

## 고정 조건

| 항목 | 값 |
| --- | --- |
| Dataset | `evals/dataset.v2.jsonl`, 30건 |
| Prompt | `coaching-output-v4.1` |
| Skill | `interview-coach-v2` |
| Criteria | 현재 Skill bundle의 `problem-solving-v4-draft.1` |
| 출력 | strict `CoachingLLMOutput` JSON Schema |
| provider routing | 기존 OpenRouter 설정 유지, `provider.require_parameters=true` |
| temperature/reasoning | 전송하지 않음, model default |
| contract repair | 최대 2 provider call / execution |
| timeout | call당 90초 |
| max completion | 2048 tokens |
| 결과 위치 | `local-results/` (Git 제외) |

Prompt/Skill/Criteria/Dataset을 이번 비교 중 수정하지 않는다.

## 1단계 — Preflight

대표 3건으로 endpoint, 모델 ID, strict schema, validator, repair, usage metadata를 먼저 확인한다.

- 정상: `coach-normal-01`
- 경계: `coach-boundary-13`
- 실패 유도: `coach-failure-30`

3모델 × 3건 = **9 executions**, 계약 실패 시 최대 18 provider calls다.

새 worktree에서 평가 venv가 아직 없다면 먼저 기존 평가 가이드와 같은 방식으로 준비한다.

```bash
bash evals/setup_env.sh
source .venv-llm-eval/bin/activate
```

계획 확인만:

```bash
.venv-llm-eval/bin/python -B evals/run_gpt6_luna_sol_comparison.py --phase preflight
```

실제 실행:

```bash
export OPENROUTER_API_KEY=...
.venv-llm-eval/bin/python -B evals/run_gpt6_luna_sol_comparison.py \
  --phase preflight --live
```

Preflight에서 확인할 항목:

1. 세 모델 모두 OpenRouter에서 모델 ID가 해석되는가.
2. strict schema 요청이 provider routing과 충돌하지 않는가.
3. 1차 contract 실패가 발생하면 repair가 의도대로 동작하는가.
4. token, latency, `usage.cost`, provider metadata가 결과에 남는가.
5. provider/timeout 오류를 의미 품질 실패로 잘못 해석하지 않는가.

## 2단계 — Full 30

Preflight에 치명적인 integration blocker가 없을 때만 실행한다.

3모델 × 30건 = **90 executions**, 계약 실패가 전부 repair로 이어지는 극단적 경우 최대 180 provider calls다.

```bash
.venv-llm-eval/bin/python -B evals/run_gpt6_luna_sol_comparison.py --phase full
```

계획을 확인한 뒤:

```bash
.venv-llm-eval/bin/python -B evals/run_gpt6_luna_sol_comparison.py \
  --phase full --live
```

비교 항목:

- 1차 contract rate / repair 후 final contract rate
- label accuracy
- intent / problem_context / own_action / result_verification
- evidence accuracy
- ID reference accuracy
- p50 / p95 latency
- 알려진 총비용과 unknown-cost call 수
- failure state와 case별 오류
- provider routing metadata

## 기존 Full 30 결과 — strict 비교에서는 무효

리뷰 과정에서 canonical runner의 `build_response_format()`이 OpenAI 계열 중
`openai/gpt-5*`만 strict JSON Schema를 사용하고 GPT-6에는 `json_object`를 사용한다는 점을
확인했다. 따라서 아래 Full 결과는 **서버 측 schema/validator 검증 결과로는 유효하지만,
문서에 정의한 strict JSON Schema 조건의 GPT-6 비교 결과로는 사용하지 않는다.**

runner를 `openai/gpt-6*`에도 strict `CoachingLLMOutput` schema를 전송하도록 수정하고
회귀 테스트를 추가했다. 이후 strict Preflight를 시도했지만 provider 사용 한도에 걸려
9 executions 모두 최종 provider error로 종료됐다. 성공 응답이 없으므로 품질 결과로 사용하지 않는다.

| 모델 | final contract | accuracy | label | evidence | 비용 | p50 / p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Flash-Lite | 30/30 | 81.0% | 87.5% | 98.6% | $0.11464 | 3.34s / 3.94s |
| GPT-6 Luna | 29/30 | 89.4% | 93.1% | 98.8% | $0.02006 | 9.03s / 36.37s |
| GPT-6 Sol | 30/30 | 97.6% | 96.7% | 98.6% | $0.35244 | 10.10s / 33.70s |

- Flash-Lite: 4개 execution이 repair를 거쳐 최종 30/30 통과했다.
- Luna: `coach-boundary-20`에서 provider error가 2회 연속 발생해 최종 1건 실패했다.
- Sol: 30건 모두 첫 호출에서 계약 통과했고 provider/contract 오류가 없었다.
- 위 수치와 대표 semantic review는 strict 재실행 전 참고값으로만 보존한다.

실행 환경 오염으로 세 모델이 모두 즉시 provider error가 난 Full run 3회는 무효 처리했다. 원인은
wrapper가 OpenRouter 전용인데도 기존 shell의 `MODEL_API_BASE_URL`을 그대로 상속한 것이며,
재발 방지를 위해 live 실행 시 OpenRouter endpoint를 wrapper에서 고정한다.

## 후속 단계

추가 provider 호출은 이번 실험 범위에서 중단한다. 모델 교체 판단에는 기존 결과를 strict-schema
근거로 사용하지 않고, 추후 별도 예산/한도에서 재평가가 필요하면 새 실험으로 진행한다.

최종 2개 후보를 정하기 전에는 repeat용 고정 wrapper를 추가하지 않는다. 후보 선택 결과를 보고
기존 `run_model_comparison.py --repeats 3`을 사용한다.

## 비밀정보와 실행 환경

새 worktree에는 기존 프로젝트의 Git 제외 `.env`가 자동 복제되지 않는다. 키 파일을 복사하거나
Git에 넣지 않고, 실행 shell에 `OPENROUTER_API_KEY`를 export한다. runner는 키 값을 결과에
저장하지 않는다.

## 현재 확인 범위

기존 Preflight/Full 30과 대표 semantic review까지 수행했으나, GPT-6 호출이 strict JSON Schema가
아닌 `json_object`였음을 확인해 strict 비교 결과에서는 제외한다. runner 보완 후 strict Preflight를
시도했지만 provider 사용 한도로 18 provider call이 모두 오류로 종료되어 추가 실호출은 중단했다.
credential 값은 결과나 Git에 저장하지 않았다.
