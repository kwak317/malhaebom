# Worklog — Prompt harness v4 → v4.1

- 일시: 2026-09-22 14:06~16:20 KST
- 작업 브랜치: `feat/prompt-harness-v4`
- 관련 문서: `docs/specs/coaching-prompt-harness-v4.md`

## 1. 목적

운영 `/api/agent` local fallback과 오프라인 모델 평가가 서로 다른 system prompt 조립 로직을
사용하던 문제를 제거하고, 출력 직전 계약 self-check를 추가한다.

## 2. 작업 전 상태

- 운영은 `load_fixed_skill_prompt()`에서 Skill 파일을 직접 이어 붙였다.
- 모델 비교는 `build_system_prompt()`에 정책 규칙을 별도로 중복 보유했다.
- 같은 Skill을 사용해도 운영과 평가 prompt가 완전히 같다는 보장이 없었다.
- 기본 prompt label은 `coaching-output-v3`였다.
- strict JSON Schema, 서버 validator, contract repair, provider retry는 이미 구현돼 있었다.

## 3. 변경 내용

- `backend/app/services/coaching_prompt.py`
  - canonical `build_coaching_system_prompt()` 추가
  - 최초 `DEFAULT_COACHING_PROMPT_VERSION=coaching-output-v4` 추가 후 A/B 결과를 반영해 `coaching-output-v4.1`로 보강
  - 출력 전 내부 self-check 8개 추가
  - 과거 실험 재현용 `coaching-output-v3` compatibility prompt 보존
  - prompt SHA-256 helper 추가
- `coaching_runtime.py`
  - `load_skill_bundle().prompt_text`와 canonical builder를 사용하도록 변경
- `evals/run_model_comparison.py`
  - 기존 `build_system_prompt()`를 compatibility wrapper로 유지하면서 canonical builder 호출
  - 기본 prompt version을 v4로 변경
  - 결과 configuration에 `prompt_sha256` 기록
- `coaching_observability.py`
  - 공통 v4 기본 version 사용
- `backend/tests/test_coaching_prompt.py`
  - v4 기본값, self-check, 운영/평가 prompt 동일성, hash 안정성 회귀 추가
- managed Langfuse prompt fallback 테스트는 prompt version이 system prompt 본문에도 반영되는 새 계약에 맞춰 갱신했다.

### v3 ↔ v4 30건 A/B 후속

- 동일 Flash-Lite, Dataset v2 30건, model-default 설정, 1회 호출로 비교했다.
- v3: 계약 63.3%, label 89.5%, evidence 96.7%, 비용 $0.0980, p50 2.90s, p95 3.58s.
- v4: 계약 50.0%, label 96.7%, evidence 95.0%, 비용 $0.1064, p50 2.95s, p95 3.23s.
- v4는 `result_verification` label 정확도가 84.2%→100%로 개선됐지만, `evidence[].text` 사용, evidence 키 누락, 비활성 criterion target 같은 형식 실패가 병목이었다.
- v4.1은 evidence 키를 정확히 `segment_id`+`quote`로 고정하고 `text`를 금지하며, criterion evidence 항상 포함과 active target ID 제한을 명시했다.
- runtime/eval 공통 repair prompt는 이전 출력 + 검증 오류를 전달하고 오류만 수정하며 새 사실 생성을 금지한다.
- 과거 v3/v4 prompt는 재현 가능성을 위해 별도 분기로 보존했다.

## 4. 검증

- `backend/tests/test_coaching_prompt.py`: 7/7 PASS
- `backend/tests/test_coaching_runtime.py`: 20/20 PASS
- prompt/runtime/eval repair 관련 묶음: 40/40 PASS
- backend 전체 중 Langfuse observability 모듈을 제외한 284/284 PASS
- 전체 286개를 처음 실행했을 때 prompt 변경 관련 실패 1개를 발견해 수정했다.
- 같은 전체 실행에서 observability 2개는 연결된 `proj2-3` Python runtime의 Langfuse SDK가
  `propagate_attributes`를 제공하지 않아 ImportError가 발생했다. prompt 변경과 별도인 환경 차이로
  해당 모듈만 제외하고 나머지 회귀를 다시 확인했다.
- 테스트용 임시 runner는 검증 후 삭제했다.

## 5. v4.1 + repair 실제 provider 재측정

- smoke `coach-normal-01`: 1차 호출에서 계약/label/evidence/ID 모두 100% 통과, 비용 $0.003378.
- 전체 Flash-Lite / Dataset v2 30건 / `--max-calls 2`:
  - 1차 계약 통과: 28/30 (93.3%)
  - repair 대상: 2건 (`coach-normal-04`, `coach-normal-09`)
  - repair 성공: 2/2
  - 최종 계약 통과: 30/30 (100%)
  - 실제 Flash 호출: 32회
  - 총 비용: $0.113911
  - 실행 단위 E2E latency: p50 3,035ms / p95 4,345ms, 최대 5,627ms
  - 전체 30건 label accuracy: 88.3%
  - evidence accuracy: 97.8%
  - ID reference accuracy: 100%
- `coach-normal-04`는 1차 exact quote validator 위반 후 repair로 복구했다.
- `coach-normal-09`는 JSON 객체가 문자열로 이중 인코딩되고 내부 evidence에 `text` 키를 사용한 schema 위반이었으며 repair로 복구했다.
- 동일 cohort 비교 시 v3가 계약 통과했던 19건에서 v4.1 label accuracy는 v3와 동일한 89.47%, v4가 계약 통과했던 15건에서는 v4.1 95.0% / v4 96.67%였다. 따라서 전체 88.3%는 기존 버전이 계약 실패로 채점하지 못했던 어려운 boundary case까지 모두 평가된 영향이 크다.
- 남은 오차는 주로 boundary 의미 판정이며 intent/C-A-V 독립, 개인 행동 주체, 확인 행위와 관찰 결과 구분이 다음 개선 대상이다.

## 6. 남은 확인

- Langfuse managed Prompt의 candidate 등록, 실제 trace 비교, production 승격/rollback은 아직 수행하지 않았다.
- 기존 v3/v4 실험 리포트·전용 실험 스크립트의 version 표기는 과거 결과 재현을 위해 유지했다.

## 7. 다음 작업

계약 하네스는 현 상태를 유지하고, boundary 실패 유형만 겨냥한 coaching-output-v4.2 candidate를
추가했다. 평가셋 문장을 직접 재사용하지 않은 합성 few-shot 5개로 intent/C-A-V 독립, 팀/개인 행동,
확인 행위/실제 관찰 결과, 정보 부족/off-topic 경계를 보강했다. v4.1은 재현용으로 보존한다.
코드 회귀는 prompt 9/9, runtime 20/20, Langfuse observability 제외 backend 286/286 PASS다.
다음은 Flash-Lite 동일 Dataset v2 30건에서 v4.1과 v4.2를 같은 --max-calls 2 조건으로 비교한 뒤,
managed Prompt candidate에서 실제 service trace를 확인하고 production 승격/rollback 여부를 결정한다.

### v4.1 control rerun ↔ v4.2 targeted A/B

- 동일 Flash-Lite / Dataset v2 30건 / --max-calls 2 조건으로 재실행했다.
- v4.1 control:
  - 1차 계약 27/30, repair 3건 모두 복구, 최종 30/30
  - 총 33호출, label 90.0%, evidence 94.7%, ID 100%, overall accuracy 83.9%
  - dimension: intent 90.0%, problem_context 90.0%, own_action 90.0%, result_verification 90.0%
- v4.2 targeted:
  - 1차 계약 26/30, repair 4건 모두 복구, 최종 30/30
  - 총 34호출, label 90.0%, evidence 93.5%, ID 100%, overall accuracy 80.9%
  - dimension: intent 90.0%, problem_context 93.3%, own_action 90.0%, result_verification 86.7%
- 개선: coach-failure-27의 intent를 undetermined로 교정, coach-boundary-17의 problem_context를 교정.
- 회귀: coach-failure-28은 off_topic→undetermined, coach-failure-30은 off_topic→partial로 이동했고, coach-boundary-20은 질문 주제 off_topic을 맞추는 대신 C/A/V까지 모두 not_observed로 과잉 일반화했다.
- 결론: targeted few-shot 5개는 한 경계를 고치면서 다른 경계를 끌어당기는 부작용이 있어 v4.2를 승격하지 않는다. 운영 기본은 v4.1 유지.

### criteria draft.2 — 판정 경계 명료화

- v4.2 few-shot 대신 운영 기본 prompt는 v4.1로 유지하고 Skill/criteria 규칙만 보강했다.
- criteria_version을 problem-solving-v4-draft.1 → problem-solving-v4-draft.2로 올렸다.
- V 규칙:
  - "~인지/여부를 확인했다"는 확인 행위로 인정하지만 실제 관찰 결과가 없으면 partial.
  - "~임을 확인했다", "~인 것을 확인했다", "~로 확인됐다"처럼 상태·수치·변화가 실제 결과로 명시되면 다른 조건도 충족하는 범위에서 met 가능.
- intent/C-A-V 규칙:
  - intent가 off_topic이어도 답변 자체의 C/A/V 근거는 독립적으로 판정하며 자동으로 낮추지 않는다.
- 기존 Dataset v2의 기대 라벨은 바꾸지 않았다.
- 평가 runner의 --case-id를 반복 지정 가능하게 확장해 targeted case 묶음 실행을 지원한다.
- 회귀: coaching eval 10/10, skill 3/3, prompt 9/9, runtime 20/20, Langfuse observability 제외 backend 287/287 PASS.
- targeted 측정 대상은 normal-04, normal-09, boundary-18, boundary-19, boundary-20과 정상 V=met 대조군 normal-02, normal-05 총 7건이다.

### criteria draft.2 targeted / full30 결과

- targeted 7건:
  - label 71.4% → 78.6%
  - overall 81.6% → 87.8%
  - evidence 95.2% → 100%
  - normal-04의 V를 met→partial로 교정했고 normal-02/05의 V met은 유지했다.
- full30:
  - draft.1 control: 1차 계약 27/30, 최종 30/30, 총 33호출, label 90.0%, overall 83.9%, evidence 94.7%
  - draft.2: 1차 계약 26/30, 최종 30/30, 총 34호출, label 88.3%, overall 80.6%, evidence 94.9%
  - draft.2 dimension: intent 90.0%, problem_context 83.3%, own_action 90.0%, result_verification 90.0%
  - draft.1 대비 problem_context가 90.0%→83.3%로 하락했다.
- 개선: normal-04 V partial 교정, boundary-20 intent off_topic 교정.
- 회귀: normal-10과 boundary-22의 problem_context, boundary-17 intent, boundary-20의 V 판정 등이 새로 어긋났다.
- 결론: draft.2 규칙은 targeted 케이스에는 효과가 있으나 전체 분포에서는 과잉 일반화가 발생하므로 운영 기준으로 승격하지 않는다.
- 실험 후 Skill/criteria 및 서비스의 criteria_version을 problem-solving-v4-draft.1로 복원했다. 평가 편의를 위한 다중 --case-id 지원은 유지했다.
- 최종 후보 복원 후 Langfuse observability 제외 backend 287/287 PASS를 다시 확인했다.
- 마지막 확인은 코드/규칙을 더 수정하지 않고 최종 후보 30건 × 3 repeats로 변동성과 case별 일관성을 측정한다.

### 최종 confirmation — v4.1 + draft.1 × 3 repeats

- 최종 후보: coaching-output-v4.1 + problem-solving-v4-draft.1 + contract repair.
- Dataset v2 30건 × 3 repeats = 90 executions.
- 계약:
  - 1차 통과 84/90 (93.3%)
  - repair 6건 / 6건 성공
  - 최종 통과 90/90 (100%)
  - 실제 provider 호출 96회
- 최종 execution 품질:
  - label accuracy 87.8%
  - evidence accuracy 96.0%
  - ID reference accuracy 100%
  - own_action 92.2%
  - problem_context 90.0%
  - result_verification 85.6%
  - intent 83.3%
- 리포트 overall 85.6%는 실패한 1차 호출까지 분모에 포함하는 call-level 집계다. repair 후 최종 90 executions만 평균하면 overall은 약 91.3%다.
- 비용/지연:
  - 총 비용 $0.292000
  - execution당 평균 비용 약 $0.003244
  - E2E p50 2,954ms / p95 5,395ms / max 6,295ms
- 반복 일관성:
  - 21/30 case는 세 번 모두 동일 label signature.
  - 7/30 case는 세 번 중 두 번 동일: boundary-14/15/16/19/22, failure-30, normal-10.
  - 2/30 case는 세 번 모두 서로 다름: boundary-17, boundary-20.
  - repair 후 contract agreement는 전 case/run에서 100%.
- 결론: contract/repair는 충분히 안정적이며, 남은 리스크는 boundary 의미 판정과 model-default stochasticity다. 추가 prompt/criteria 튜닝은 dataset 과적합 위험이 커 여기서 종료한다.

> 2026-09-30 D4 사람 검토에서 `coach-boundary-17`의 V expected를 `partial → undetermined`로 수정했다. 당시 90개 저장 출력을 provider 재호출 없이 재채점한 결과 label accuracy는 316/360(87.8%) → 313/360(86.9%), V accuracy는 77/90(85.6%) → 74/90(82.2%)로 정정됐다. 세 run의 모델 출력 V가 모두 `partial`이어서 V 정답 3개가 오답으로 바뀌었으며 계약/evidence/ID/비용/지연과 모델 출력 자체는 변하지 않았다. 상세는 `docs/experiments/2026-09-30_d4-boundary17-offline-regrade.md`를 따른다.

### PR 정리

- 최종 채택하지 않은 coaching-output-v4.2 실행 코드와 전용 테스트는 PR에서 제거하고, 비교 결과만 이 worklog에 보존했다.
- 최종 구현은 coaching-output-v4.1 + problem-solving-v4-draft.1 + contract repair만 남겼다.
- 정리 후 prompt harness 테스트 8/8, Langfuse observability 모듈 제외 backend 286/286 PASS를 확인했다.
- Review Core는 642줄로 400줄 권장선을 넘지만 800줄 hard limit 이하다. canonical prompt, runtime repair, evaluator의 동일 repair/repeat 지원이 하나의 출력 계약 하네스를 구성하므로 별도 PR로 분리하면 검증 경계가 끊긴다. 대신 runtime/prompt와 eval/docs를 논리적 커밋으로 분리한다.
