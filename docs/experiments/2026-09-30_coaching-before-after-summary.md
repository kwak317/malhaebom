# 2026-09-30 — 코칭 평가 Before / After 요약

## 목적

강사 피드백의 “개선 전후 비교가 비어 있고, 결과 파일이 저장소 밖에 있음”을 보완하기 위해 이미 수행한 코칭 평가를 **동일 2026-09-22 Dataset v2 snapshot / 동일 Flash-Lite 조건**으로 다시 연결하고, 저장소 안에서 확인 가능한 요약 artifact로 고정한다.

이 문서는 새 provider 호출이나 새 baseline 측정이 아니다. **기존 저장 결과와 Worklog의 수치를 한 곳에 연결한 redacted 요약 artifact**다. D7 공식 baseline 선정이나 D11~D12 최종 개선 평가는 이 문서로 대체하지 않는다.

## 비교 범위

- 모델: Gemini 3.5 Flash-Lite
- 평가셋: 2026-09-22 당시 Dataset v2 30건 snapshot (v3/v4/v4.1/v4.2 비교 공통)
- 현재 ground truth: 2026-09-30 사람 검토에서 `coach-boundary-17` V expected 1건이 수정됐으며, 최종 반복 측정은 별도 offline regrade 수치로 표시
- 주요 원본 기록: `docs/worklogs/2026-09-22_1406_prompt-harness-v4.md`
- 사람 ground-truth 정정: `docs/experiments/2026-09-30_d4-boundary17-offline-regrade.md`
- 현재 dataset 정책: `evals/README.md`
- 비용은 provider usage에 기록된 알려진 비용의 합계다.
- label/evidence는 **contract 통과 결과만 분모에 포함**하므로 contract 통과율이 크게 다른 실험의 label 수치를 단순한 전체 30건 정확도처럼 비교하지 않는다.

## 1. 동일 조건 Prompt A/B — v3 → v4

2026-09-22에 동일 Flash-Lite, 동일 Dataset v2 30건, model-default, **1회 호출** 조건으로 비교했다.

| 지표 | Before: v3 | After: v4 | 변화 |
| --- | ---: | ---: | ---: |
| contract 통과 | 63.3% | 50.0% | -13.3%p |
| label accuracy* | 89.5% | 96.7% | +7.2%p |
| evidence accuracy* | 96.7% | 95.0% | -1.7%p |
| result_verification label* | 84.2% | 100% | +15.8%p |
| 총 비용 | $0.0980 | $0.1064 | +$0.0084 |
| latency p50 | 2.90s | 2.95s | +0.05s |
| latency p95 | 3.58s | 3.23s | -0.35s |

\* label/evidence 계열은 contract 통과 결과만 채점되므로 v3와 v4의 분모가 다르다.

### 관찰

- v4는 결과 검증(V) 의미 판정은 좋아졌지만 contract 통과율이 63.3% → 50.0%로 떨어졌다.
- 주요 형식 실패는 `evidence[].text` 사용, evidence 키 누락, 비활성 criterion target 참조였다.
- 따라서 의미 품질만 올리고 contract 안정성을 잃는 변경은 운영 승격 조건을 만족하지 못했다.

## 2. Contract robustness 개선 — v4 → v4.1 + repair

v4.1은 v4에서 발견한 형식 실패를 줄이도록 evidence 키와 target ID 계약을 명시하고, 계약 실패 시 **이전 출력과 validator 오류만 전달해 오류만 고치는 1회 repair**를 추가했다.

| 지표 | v4 one-call | v4.1 + repair | 해석 |
| --- | ---: | ---: | --- |
| 1차 contract | 50.0% | 28/30 (93.3%) | 형식 안정성 크게 개선 |
| 최종 contract | 50.0% | 30/30 (100%) | repair 2/2 복구 |
| label accuracy* | 96.7% | 88.3% | contract coverage 차이로 단순 delta 금지 |
| evidence accuracy* | 95.0% | 97.8% | 동일 이유로 보조 비교 |
| ID reference | 기록값 기준 | 100% | v4.1 최종 전건 유효 |
| 총 비용 | $0.1064 | $0.113911 | +$0.007511 |
| latency p50 | 2.95s | 3.035s | +0.085s |
| latency p95 | 3.23s | 4.345s | +1.115s |

\* v4는 contract 통과한 15건 중심이고 v4.1은 repair 후 30건 모두 contract 통과해 채점되므로 label 수치의 모집단이 다르다.

### 대표 개선 case

- `coach-normal-04`: exact quote validator 위반 → repair 후 정상 복구.
- `coach-normal-09`: JSON 이중 인코딩 + evidence `text` 키 사용 → repair 후 정상 복구.

이 두 case는 repair가 의미를 새로 생성하는 대신 **계약 오류만 수정**하도록 설계한 이유를 보여준다.

## 3. 과개선 방지 사례 — v4.2 targeted candidate

v4.1 이후 boundary 문제만 겨냥한 v4.2 targeted candidate도 동일 Flash-Lite / Dataset v2 30건 / `--max-calls 2` 조건으로 비교했다.

| 지표 | v4.1 control | v4.2 targeted |
| --- | ---: | ---: |
| 1차 contract | 27/30 | 26/30 |
| 최종 contract | 30/30 | 30/30 |
| 호출 수 | 33 | 34 |
| label accuracy | 90.0% | 90.0% |
| evidence accuracy | 94.7% | 93.5% |
| ID reference | 100% | 100% |
| overall accuracy | 83.9% | 80.9% |

대표적으로 `coach-failure-27` intent와 `coach-boundary-17` problem_context는 개선됐지만, `coach-failure-28`, `coach-failure-30`, `coach-boundary-20`에서는 새로운 회귀가 발생했다. 따라서 targeted few-shot 후보는 승격하지 않았다.

이 사례는 “일부 case 개선”을 전체 품질 개선으로 오해하지 않고 **같은 평가셋 전체 회귀를 확인한 뒤 discard**한 기록이다.

## 4. 최종 반복 측정과 현재 ground truth

최종 보존 후보는 `coaching-output-v4.1 + problem-solving-v4-draft.1 + contract repair`이며 Dataset v2 30건 × 3회, 총 90 executions로 반복 측정했다.

2026-09-30 사람 검토에서 `coach-boundary-17`의 V expected가 `partial → undetermined`로 수정됐기 때문에, 저장된 90개 출력은 provider 재호출 없이 현재 ground truth로 offline 재채점했다.

| 지표 | 현재 확정값 |
| --- | ---: |
| 1차 contract | 84/90 (93.3%) |
| repair | 6/6 성공 |
| 최종 contract | 90/90 (100%) |
| label accuracy | 313/360 (86.9%) |
| evidence accuracy | 96.0% |
| ID reference | 100% |
| intent | 75/90 (83.3%) |
| problem_context | 81/90 (90.0%) |
| own_action | 83/90 (92.2%) |
| result_verification | 74/90 (82.2%) |
| 총 비용 | $0.292000 |
| execution당 평균 비용 | 약 $0.003244 |
| latency p50 | 2,954ms |
| latency p95 | 5,395ms |
| max latency | 6,295ms |

반복 일관성은 21/30 case가 세 번 모두 같은 label signature였고, 7/30은 2/3 일치, 2/30(`boundary-17`, `boundary-20`)은 세 번 모두 달랐다. contract agreement는 전 case/run에서 100%였다.

## 5. 결론

이전 실험을 한 줄의 “정확도 상승”으로 요약하면 중요한 trade-off가 사라진다.

- v3 → v4에서는 일부 의미 판정이 좋아졌지만 contract 안정성이 악화됐다.
- v4 → v4.1 + repair에서는 contract가 최종 100%까지 회복됐고, 그 대가로 호출·비용·tail latency가 조금 늘었다.
- v4.2 targeted는 일부 boundary를 고쳤지만 다른 case 회귀가 생겨 discard했다.
- 최종 v4.1 반복 측정은 contract 안정성은 높았지만 boundary 의미 판정과 stochasticity가 남은 리스크임을 보여준다.

따라서 현재 저장소가 보여주는 개선 과정은 **“품질 지표 하나를 최대화”가 아니라 contract 안정성, 의미 정확도, evidence, 비용, latency를 같은 평가셋에서 함께 관찰하고 회귀 후보를 버린 과정**이다.

## 재현·출처

- Dataset/채점 정책: `evals/README.md`
- Dataset: `evals/dataset.v2.jsonl`
- Prompt harness 원본 기록: `docs/worklogs/2026-09-22_1406_prompt-harness-v4.md`
- D4 사람 검토: `docs/worklogs/2026-09-30_d4-human-review.md`
- ground-truth correction 재채점: `docs/experiments/2026-09-30_d4-boundary17-offline-regrade.md`
- 저장 결과 재채점 CLI: `evals/regrade_saved_results.py`

저장된 원본 provider 결과를 다시 채점할 때는 다음 형태를 사용한다.

```bash
PYTHONPATH=backend:. .venv-llm-eval/bin/python -B -m evals.regrade_saved_results \
  --input <saved-all-attempts.json> \
  --dataset evals/dataset.v2.jsonl \
  --output-dir <new-output-dir>
```

원본 provider 응답·credential·개인정보는 이 요약 artifact에 복제하지 않는다. 원본이 로컬/Git 제외 경로에 있더라도, 본 문서에 필요한 비교 수치·조건·대표 case·한계를 저장소에서 확인 가능하게 남긴다.
