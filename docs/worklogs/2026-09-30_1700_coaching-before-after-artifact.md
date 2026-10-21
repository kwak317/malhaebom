# 2026-09-30 — 코칭 Before / After 평가 artifact 고정

## 목적

강사 피드백 보완 체크의 관찰·평가 항목을 위해 기존 Prompt/criteria/model 실험 결과를 동일 Dataset v2 기준으로 연결하고, 저장소 안에서 확인 가능한 redacted Before / After 요약 artifact를 만든다.

## 작업 전 상태

- v3/v4/v4.1/v4.2 비교와 최종 v4.1 30건 × 3회 측정은 이미 수행돼 있었다.
- D4 사람 검토와 boundary-17 ground-truth correction도 완료돼 있었다.
- 하지만 강사에게 보여줄 수 있는 한 문서에서 contract, label, evidence, latency, cost와 대표 개선/회귀 case가 연결되어 있지 않았다.
- 일부 raw 결과는 Git 제외 로컬 경로에 있어 저장소만 봐서는 전체 비교 흐름을 파악하기 어려웠다.

## 수행한 작업

- `docs/experiments/2026-09-30_coaching-before-after-summary.md`를 추가했다.
- 동일 Flash-Lite / Dataset v2에서 v3→v4 one-call 비교, v4→v4.1+repair robustness 개선, v4.2 targeted discard 근거를 연결했다.
- contract, label, evidence, latency, cost를 같은 문서에서 비교했다.
- `coach-normal-04`, `coach-normal-09` repair 개선과 v4.2의 대표 회귀 case를 기록했다.
- 최종 v4.1 30건 × 3회 결과는 D4 사람 검토 후 ground truth 기준 수치로 고정했다.
- 추가 강사 피드백 체크리스트의 관찰·평가 항목을 완료 처리했다.

## 주요 판단과 이유

- v3/v4의 label/evidence는 contract 통과 결과만 분모에 들어가므로 숫자만 보고 단순 우열을 주장하지 않는다.
- v4.1은 repair 도입으로 max-calls 조건이 달라졌으므로 비용·latency trade-off를 함께 기록한다.
- v4.2는 일부 case를 개선했지만 다른 case 회귀가 있어 “개선 후보를 버린 근거”로 보존한다.
- 이 artifact는 D7 공식 baseline과 D11~D12 최종 개선 평가를 대신하지 않는다. D7 작업 중인 팀원과 범위를 충돌시키지 않는다.

## 변경 파일

- `docs/experiments/2026-09-30_coaching-before-after-summary.md`
- `docs/project2-checkpoint-work-cards.md`
- `docs/worklogs/README.md`
- `docs/worklogs/2026-09-30_1700_coaching-before-after-artifact.md`

## 검증

- 수치는 기존 `docs/worklogs/2026-09-22_1406_prompt-harness-v4.md`와 `docs/experiments/2026-09-30_d4-boundary17-offline-regrade.md`에 기록된 값만 사용했다.
- 현재 Dataset v2 정책에서 label/evidence가 contract 통과 결과 대상임을 artifact에 명시했다.
- D4 correction은 새 모델 실행이 아니라 동일 저장 출력의 offline regrade임을 분리했다.
- raw provider output, credential, 개인정보는 artifact에 포함하지 않았다.

## 발견한 문제와 한계

- v3/v4와 v4.1+repair는 max-calls가 다르므로 contract robustness 개선과 호출 비용 증가를 동시에 해석해야 한다.
- v3/v4의 label 정확도와 v4.1의 label 정확도는 contract coverage가 달라 전체 30건 동일 분모 수치처럼 직접 비교할 수 없다.
- historical v3/v4 결과는 2026-09-22 당시 Dataset v2 ground truth 기준이고, boundary-17 correction을 v3/v4 raw 출력에 다시 적용한 저장소 내 결과는 없다.

## 다음 작업

- D7 담당 작업에서 공식 baseline을 별도로 확정한다.
- D11~D12에서는 그 baseline과 최종 서비스 버전을 동일 고정 평가셋으로 다시 비교한다.
