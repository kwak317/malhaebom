# 2026-09-30 — D4 boundary-17 ground-truth 변경 offline 재채점

## 목적

D4 사람 검토에서 `coach-boundary-17`의 `result_verification` expected가 `partial`에서 `undetermined`로 수정됐다. 모델·Prompt·Skill을 다시 실행하지 않고 2026-09-22 최종 Flash-Lite 30건 × 3회 저장 응답을 새 ground truth로 다시 채점해 기존 품질 수치를 정정한다.

이 작업은 **새 모델 실험이 아니라 ground-truth correction에 따른 offline regrade**다.

## 재채점 대상

- 원본 실행: `final-v4-1-draft1-repeat3/comparison.json`
- 생성 시각: 2026-09-22
- 모델: Gemini 3.5 Flash-Lite
- Prompt: `coaching-output-v4.1`
- Skill criteria: `problem-solving-v4-draft.1`
- Dataset: Dataset v2 30건
- 반복: 3회
- 최종 executions: 90
- 실제 provider calls: 96
- provider 재호출: **없음**

원본 `comparison.json`의 raw/validated output, provider, token, cost, latency는 수정하지 않았다. 현재 `evals/dataset.v2.jsonl`과 `score_response()`를 사용해 저장된 validated output만 다시 채점했다.

로컬 결과는 Git 제외 경로인 다음 위치에 보존한다.

`local-results/d4-boundary17-regrade-20260930/`

- `summary.json`
- `case17-regraded.json`
- `REPORT.md`

## 변경된 ground truth

| 항목 | 변경 전 | 변경 후 |
| --- | --- | --- |
| case | `coach-boundary-17` | 동일 |
| dimension | `result_verification` | 동일 |
| expected | `partial` | `undetermined` |
| V 보조지표 | 해당 없음 | `ambiguous_target` |

사람 검토 근거는 다음과 같다.

> 여러 프로젝트와 행동이 섞여 있고 “성능이 좋아졌다”는 주장이 어느 프로젝트·행동의 결과인지 특정할 수 없다.

따라서 결과 언급 자체는 있으나 귀속 대상을 정할 수 없는 `undetermined`가 적절하다.

## case 17 저장 출력 재채점

세 번의 기존 모델 출력은 모두 V=`partial`이었다.

| run | 저장 모델 출력 V | 기존 expected | 새 expected | 기존 채점 | 새 채점 |
| ---: | --- | --- | --- | --- | --- |
| 1 | `partial` | `partial` | `undetermined` | 정답 | 오답 |
| 2 | `partial` | `partial` | `undetermined` | 정답 | 오답 |
| 3 | `partial` | `partial` | `undetermined` | 정답 | 오답 |

따라서 최종 90 executions의 V 정답 수가 정확히 3개 감소한다.

## 최종 90 executions 전후

| 지표 | 변경 전 | 변경 후 | 차이 |
| --- | ---: | ---: | ---: |
| 최종 contract | 90/90 (100%) | 90/90 (100%) | 동일 |
| 전체 label | 316/360 (87.8%) | 313/360 (86.9%) | -0.8%p |
| intent | 75/90 (83.3%) | 75/90 (83.3%) | 동일 |
| problem context | 81/90 (90.0%) | 81/90 (90.0%) | 동일 |
| own action | 83/90 (92.2%) | 83/90 (92.2%) | 동일 |
| result verification | 77/90 (85.6%) | 74/90 (82.2%) | -3.3%p |
| evidence accuracy | 96.0% | 96.0% | 동일 |
| ID reference | 100% | 100% | 동일 |
| 비용 | $0.292000 | $0.292000 | 동일 |

추가로 기존 report의 call-level overall accuracy는 85.6% → 85.1%, repair 후 최종 90 executions의 overall mean은 약 91.3% → 90.8%로 정정된다.

## 해석

이번 변화는 모델의 새 추론 결과나 회귀가 아니다. **동일한 90개 저장 응답을 더 정확하게 확정된 사람 ground truth로 다시 채점한 결과**다.

따라서 다음 항목은 그대로 유지한다.

- 1차 contract 84/90
- repair 6/6 성공
- 최종 contract 90/90
- evidence accuracy 96.0%
- ID reference accuracy 100%
- 비용 $0.292000
- 기존 latency 측정
- 90개 모델 출력 및 96개 provider call 원본

D7 공식 baseline을 정할 때는 수정 전 87.8%가 아니라 **D4 재채점 후 label 86.9%, V 82.2%**를 사용한다. 다만 D7의 “30건 중 통과 수” 기준 자체는 별도로 확정해야 한다.

## 한계

- 이번 변경은 한 개 ground-truth label만 수정한 재채점이다.
- 사람 검토는 김재훈 단일 검토자이며 inter-rater agreement는 없다.
- V 보조지표는 사람 검토 metadata이고 현재 모델 출력 계약이나 자동 점수의 별도 차원은 아니다.
- 이 재채점은 공식 100건 이상 structured-output 계약 실행을 대신하지 않는다.
