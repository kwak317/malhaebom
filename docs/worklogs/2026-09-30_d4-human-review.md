# 2026-09-30 — D4 평가셋 30건 사람 검토

## 목적

Project2 D4의 “문항마다 판정자 이름과 판정 근거 한 줄” 요구를 Dataset v2 30건에 대해 실제 사람 검토로 완료하고, 결과 확인(V) 판정의 세부 차이를 자동 점수와 분리한 보조지표로 기록한다.

## 작업 전 상태

- `evals/dataset.v2.jsonl` 30건은 존재했지만 provenance가 `independent_review_pending` 상태였다.
- 과거 30건 evidence 전수 점검과 label 재검토 기록은 있었지만, D4용 case별 최종 사람 판정 기록은 없었다.
- V의 상위 판정은 `met / partial / not_observed / undetermined` 4종이었으며, 같은 상위 판정 안의 원인 차이는 별도 필드로 구분하지 않았다.

## 수행한 작업

1. 김재훈이 30건 전체의 입력 원문과 expected C/A/V 판정을 직접 확인했다.
2. 29건은 기존 판정을 확정했다.
3. `coach-boundary-17`은 여러 프로젝트와 행동이 섞여 결과 귀속 대상을 특정할 수 없어 V를 `partial → undetermined`로 수정 확정했다.
4. V 보조지표를 다음 7종으로 정의했다.
   - `verified`
   - `verification_only`
   - `result_only`
   - `omitted`
   - `explicitly_unverified`
   - `ambiguous_target`
   - `conflicting_results`
5. 보조지표는 사람 검토용 metadata로만 사용하고 기존 구조화 출력 계약, contract rate, label accuracy, evidence accuracy에는 포함하지 않도록 했다.
6. `evals/reviewer-assignment.md`에 30건의 판정자, 최종 근거, V 보조지표와 상태를 기록했다.
7. Dataset provenance를 사람 검토 완료 상태와 단일 검토자 한계가 드러나도록 갱신했다.
8. 9/22 최종 Flash-Lite 30건 × 3회 저장 결과를 새 expected 기준으로 offline 재채점했다. provider는 다시 호출하지 않았다.

## 주요 판단과 이유

- `undetermined`는 단순 정보 부족이 아니라 정보가 있으나 상충하거나 귀속 대상을 특정할 수 없는 경우에만 사용한다.
- `not_observed` 안에서는 결과 언급이 없는 경우(`omitted`)와 결과 미확인을 명시한 경우(`explicitly_unverified`)를 구분한다.
- `partial` 안에서는 확인 행위만 있는 경우(`verification_only`)와 결과 주장만 있는 경우(`result_only`)를 구분한다.
- V 보조지표는 현재 모델 계약을 확장하지 않는다. 기존 실험의 비교 가능성을 유지하기 위해 사람 검토와 오류 분석에만 사용한다.
- 이번 검토는 단일 검토자 방식이므로 검토자 간 일치도는 측정하지 않는다.

## 변경 파일

| 파일 | 변경 |
| --- | --- |
| `evals/dataset.v2.jsonl` | 30건 provenance 갱신, boundary-17 V 수정 |
| `evals/reviewer-assignment.md` | 30건 최종 사람 검토 기록과 V 보조지표 정의 |
| `backend/tests/test_coaching_eval_v2.py` | boundary-17 기대 행렬 수정 |
| `evals/README.md` | V 보조지표와 사람 검토 완료 상태 설명 |
| `docs/CURRENT_STATE.md` | 평가 현재 상태에 D4 사람 검토 완료 반영 |
| `docs/project2-checkpoint-work-cards.md` | D4 완료 상태 반영 |
| `docs/worklogs/README.md` | 본 Worklog 링크 추가 |
| `docs/experiments/2026-09-30_d4-boundary17-offline-regrade.md` | 9/22 최종 90 executions의 ground-truth correction 재채점 기록 |
| `EVAL_REPORT.md` | D4 재채점 전후 품질 수치 반영 |

## 검증

- Dataset v2 30건이 모두 사람 검토 완료 provenance를 가지는지 확인한다.
- `evals/reviewer-assignment.md`의 30건이 모두 `확정` 또는 `수정 확정`인지 확인한다.
- V 보조지표 분포는 `verified 8 / verification_only 4 / result_only 3 / omitted 10 / explicitly_unverified 4 / ambiguous_target 1 / conflicting_results 0`이다.
- `backend/tests/test_coaching_eval_v2.py`를 실행해 기대 행렬과 dataset 정합성을 확인한다.
- 기존 `final-v4-1-draft1-repeat3`의 Flash-Lite 90 executions를 provider 재호출 없이 재채점했다.
- 재채점 결과: label 316/360(87.8%) → 313/360(86.9%), V 77/90(85.6%) → 74/90(82.2%). intent/C/A, evidence 96.0%, ID 100%, 계약/비용/지연은 변하지 않았다.
- 로컬 산출물: `local-results/d4-boundary17-regrade-20260930/`

## 발견한 문제와 한계

- 단일 검토자이므로 검토자 간 일치도를 제공할 수 없다.
- V 보조지표는 현재 모델 출력 필드가 아니므로 자동 측정 지표가 아니라 사람 검토 metadata다.
- 이 변경은 100건 이상 공식 계약 준수율이나 D7 baseline 확정을 대신하지 않는다.

## 다음 작업

- D7 공식 baseline으로 사용할 30건 실행을 고정하고 “30건 중 통과 수”를 기록한다.
- D7 baseline에서는 D4 재채점 후 수치를 사용하고, 원래 9/22 수치와 ground-truth 정정 수치를 구분해 기록한다.
