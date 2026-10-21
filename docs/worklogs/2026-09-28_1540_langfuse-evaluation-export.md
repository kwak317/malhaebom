# Langfuse 평가 결과 Experiment export

- 날짜: 2026-09-28
- 브랜치: `feat/langfuse-evaluation-export`
- 관련 Spec: `docs/specs/langfuse-operations.md`

## 목적

기존 `evals/run_model_comparison.py`의 완료된 `comparison.json`을 모델 provider 재호출 없이 Langfuse Dataset Run/Experiment와 Score에 연결한다. 기존 평가의 모델·Prompt·Skill·Dataset·grader 버전과 품질/비용/지연 결과를 Langfuse UI에서 비교할 수 있게 하되, import 자체를 새 모델 실행으로 오인하지 않도록 구분한다.

## 변경

- `evals/export_langfuse_experiments.py` 추가
  - comparison report에서 execution별 마지막 contract attempt만 선택
  - candidate × repeat별 별도 Experiment run 생성
  - Langfuse Dataset item의 `metadata.case_id`로 기존 결과 연결
  - `metadata.synthetic=true`가 아닌 Dataset item은 거부
  - contract/rule/label/evidence/ID/semantic/critical/policy Score와 원래 latency/cost를 기록
  - import metadata에 `provider_recalled=false` 기록
  - report 생성 시각 기반 결정적 run name으로 중복 import 방지
  - dry-run 기본, `--apply`에서만 외부 Langfuse 변경
- `backend/tests/test_langfuse_experiment_export.py` 추가
- `evals/README.md`, Langfuse 운영 Spec에 실행법과 해석 경계 추가

## SDK 확인

- 저장소 의존성은 `langfuse>=4.7,<5`다.
- 로컬 `proj2-3` Python runtime은 아직 Langfuse `2.60.10`으로 오래되어 Experiment Runner API가 없다.
- 별도 최신 runtime의 Langfuse `4.15.1`에서 `Langfuse.run_experiment`의 `name/run_name/data/task/evaluators/max_concurrency/metadata` 계약을 확인했다.
- export는 v4 Experiment Runner가 없을 때 requirements 환경을 사용하라는 명확한 오류로 중단한다.

## 검증

- system Python: 7 tests OK, Langfuse SDK 미설치 test 1건 skip
- `proj2-3` runtime: 7 tests OK, stale Langfuse 2.60.10 계약 test 1건 skip
- 최신 Langfuse 4.15.1 runtime: 새 adapter 7 + 기존 Langfuse assets 2 + observability 5 + coaching runtime 21 = 총 35 tests OK
- 실제 Langfuse 원격 프로젝트에는 이번 작업에서 `--apply`를 실행하지 않았다.
- canonical `dataset.v2.jsonl` 30건으로 mock 2후보 × 2회(총 120 offline executions)를 생성해 CLI dry-run을 확인했다. provider 호출과 Langfuse write는 모두 0이며 candidate × repeat별 4개 Experiment run(각 30 case)이 계획됐다.
- dry-run에서 ISO timestamp가 과도하게 길어진 run name을 발견해 UTC `YYYYMMDDTHHMMSSZ` 형식으로 정규화했고 회귀 테스트를 추가했다.

## 남은 확인

실제 `comparison.json`과 팀 Langfuse credentials를 사용해 먼저 dry-run을 확인한 뒤 `--apply`를 1회 실행하고, Langfuse UI에서 Dataset Run, item Score, candidate/repeat 비교가 기대대로 표시되는지 확인한다.
