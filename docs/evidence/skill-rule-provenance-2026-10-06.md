# Skill 규칙 provenance · 전문가 검토 유보 상태 — 2026-10-06

## 목적

프롬프트 설계 체크리스트의 다음 두 항목을 E2E 없이 저장소 수준에서 정리한다.

1. Skill 규칙마다 이유·출처·검수 상태를 추적한다.
2. 확정되지 않은 전문가 기준은 명시적으로 `유보` 상태로 표시한다.

## 구현

`skills/interview-coach/rule-provenance.json`을 추가했다.

각 criterion ID마다 다음 정보를 기록한다.

- `rationale`: 해당 기준을 두는 이유. 현재 `criteria.json`의 description과 일치시켜 drift를 막는다.
- `source.path`: 실제 판정 문구를 관리하는 질문 유형 문서.
- `source.section`: 추적할 criterion ID.
- `expert_review.status`: `deferred` 또는 `reviewed`.
- `expert_review.display_status`: 사람이 보는 상태. 2026-10-09 기준 `김창민 검토 완료`.
- `expert_review.reviewer`: 검토완료 전에는 null.
- `expert_review.reason`: 유보 사유.

## 현재 상태

- canonical `criteria.json`의 criterion은 총 **33개**다.
- 33개 모두 provenance entry가 정확히 하나씩 존재한다.
- 2026-10-06에는 33개 모두 `deferred / 유보`였으며 reviewer=null로 기록했다.
- 2026-10-09 사용자가 김창민(IT 업계 면접관 경험 있음)의 33개 전체 검토 완료를 확인했다. 현재는 `reviewed / 김창민 검토 완료`, reviewer=김창민이다.
- 이름·경험·검토 완료는 사용자 제공 정보다. 별도의 검토 원문은 첨부되지 않았으며 `expert_review_confirmation`에 이 근거와 기록 날짜를 남겼다.
- provenance는 추적 메타데이터로만 사용하며 모델 system prompt에는 합성하지 않는다. 따라서 이번 변경 자체가 코칭 모델 입력이나 Skill hash를 바꾸는 근거가 되지 않는다.

## 출처 정책

- `problem_solving` criterion → `problem-solving.md`
- `preset_interview` criterion → `preset-interview.md`

실제 판정 정의는 기존 Skill 문서와 `criteria.json`에 계속 남는다. provenance 파일은 새 canonical rule body가 아니라, 이유·출처·전문가 검수 상태를 연결하는 sidecar다.

## 회귀 검증

`backend/tests/test_coaching_skill.py`에서 다음을 확인한다.

- provenance의 skill/criteria version이 canonical catalog와 일치
- provenance ID 집합이 canonical criterion ID 집합과 정확히 일치
- 각 rationale이 criterion description과 일치
- source 파일이 실제 존재
- 현재 33개 모두 `reviewed / 김창민 검토 완료`이며 reviewer가 김창민임
- 사용자 확인 출처와 기록 날짜가 존재하고 규칙별 사유가 비어 있지 않음

## 체크리스트 판정

- **Skill 규칙마다 이유·출처·검수 상태 기록:** criterion 단위 추적 기준으로 완료 처리 가능.
- **확정되지 않은 전문가 기준을 유보로 표시:** 현재 모든 criterion에 명시적 유보 상태를 기록했으므로 완료 처리 가능.

이번 변경은 전문가 검토 메타데이터만 갱신한다. 규칙 본문·Prompt·모델·평가 정답·운영 배포는 변경하지 않는다. [Worklog](../worklogs/2026-10-09_expert-rule-review-confirmation.md).
