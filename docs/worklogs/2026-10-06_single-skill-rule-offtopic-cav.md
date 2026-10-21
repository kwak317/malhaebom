# Worklog — Skill 규칙 1개 A/B 라운드 준비

- 일시: 2026-10-06
- 범위: provider/E2E 호출 없이 단일 규칙 후보와 재현 가능한 비교 runner를 준비.
- 기준 branch: #182/#184 병합 후 main.

## 선택한 약한 구간

10/6 최신 운영 구성 30건 × 3회 반복평가에서 `coach-boundary-19`는 세 번 모두 자동 통과에 실패했다. 사람 확정 Dataset v2의 기대값은 intent=`off_topic`이어도 C/A/V를 독립 판정하여 `problem_context=met`, `own_action=met`, `result_verification=partial`이다.

기존 Skill에도 off-topic과 C/A/V를 분리하라는 규칙이 있지만, 실제 모델은 `problem_context`를 반복해서 partial로 낮췄다. 첫 번째 단일 규칙 실험은 이 경계만 강화한다.

## 단일 변경

baseline:
`Negative: Do not mark C/A/V as missing merely because intent is off_topic.`

candidate:
`Negative: Do not lower C/A/V solely because intent is off_topic; assess each active C/A/V criterion only from its own stated difficulty, first-person action, or observed result.`

다른 Skill 규칙, Dataset, Prompt, 모델, grader, generation 설정은 바꾸지 않는다. 모델에 노출되는 Skill version metadata도 동일하게 유지해 모델 입력 차이는 이 한 규칙 문장뿐이도록 한다.

## 추가 파일

- `evals/skill_rule_candidates/off-topic-cav-independence-v1.json`: 이전/변경 규칙과 고정 조건
- `evals/run_single_skill_rule_comparison.py`: baseline/candidate A/B runner
- `backend/tests/test_single_skill_rule_comparison.py`: 단일 규칙 diff와 plan invariant 검사

## 실행 순서

1. target smoke: `coach-boundary-19` baseline/candidate 각 1회
2. target 방향이 개선되면 전체 Dataset v2 30건 × candidate 2종 × 2회
3. target case와 새 회귀 case를 사람 검토
4. KEEP/DISCARD 확정 후 `EVAL_REPORT.md`와 체크리스트 갱신

실제 provider 호출은 이번 PR 준비 단계에서는 수행하지 않는다.

## 리뷰 반영

- 첫 리뷰에서 target 개선을 `problem_context` 하나만 보던 오류를 C/A/V 전체 target criterion 집합으로 수정했다.
- 후속 점검에서는 target hit 총합만 증가하면 특정 criterion 회귀가 가려질 수 있어, **최소 한 target criterion 개선 + target criterion별 무회귀**를 자동 KEEP 후보의 필수 조건으로 강화했다.
- 전체 label accuracy와 contract rate 무회귀 조건도 그대로 유지하며, 최종 KEEP/DISCARD는 사람 검토 뒤 확정한다.

## 2026-10-06 live smoke 결과

- 대상: `coach-boundary-19`, baseline/candidate 각 1회.
- 모델: `google/gemini-3.5-flash-lite`.
- 계약: baseline 1/1, candidate 1/1.
- target criterion hit: baseline 2/3 → candidate 1/3.
  - `problem_context`: 0 → 0
  - `own_action`: 1 → 0
  - `result_verification`: 1 → 1
- 전체 label accuracy: 75% → 50%.
- 비용: baseline $0.0060272 + candidate $0.0060716 = **$0.0120988**.
- 지연: baseline 4545.843ms, candidate 4485.538ms.

candidate는 `own_action`을 기존 met에서 partial로 낮췄다. 답변에 “제가 투표를 진행했고”라는 직접 행동 근거가 있는데도, candidate는 “백엔드 프로젝트 내 개발 조치가 아니다”라는 질문 적합성 조건을 C/A/V 자체 판정에 다시 섞었다. 즉 이번 한 줄 강화는 목표한 intent/C/A/V 분리를 개선하지 못했고 오히려 target 회귀를 만들었다.

자동 gate는 `DISCARD_CANDIDATE`를 반환했다. smoke에서 target criterion 회귀가 확인됐으므로 full 30건×2회 확대 평가는 실행하지 않는다. 최종 DISCARD는 target 출력에 대한 사람 확인 후 확정한다.
