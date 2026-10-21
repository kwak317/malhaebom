# Worklog — Skill 규칙 provenance와 전문가 검토 유보 상태

- 일시: 2026-10-06
- 범위: E2E/provider 호출 없음.

## 목적

프롬프트 설계 체크리스트의 규칙별 이유·출처·검수 상태와 전문가 기준 유보 상태를 실제 파일로 추적한다.

## 변경

- `skills/interview-coach/rule-provenance.json` 신규 추가
  - canonical criterion 33개 전체 coverage
  - rationale = criteria description
  - source = 질문 유형 문서 + criterion ID
  - expert review = `deferred / 유보`
  - reviewer는 검토완료 전까지 null
- `docs/specs/coaching-skill-runtime.md`에 provenance sidecar 역할과 비모델입력 정책 명시
- `backend/tests/test_coaching_skill.py`에 coverage/version/source/review-state 회귀 검사 추가
- 증거 문서: `docs/evidence/skill-rule-provenance-2026-10-06.md`

## 중요한 경계

이번 provenance 파일은 추적 메타데이터다. 모델 Prompt/Skill body에 합성하지 않으며 현재 코칭 규칙의 의미를 새로 바꾸지 않는다. 외부 면접관 검토를 수행한 것으로 주장하지 않는다.

## 기대 체크리스트 변화

- Skill 규칙별 이유·출처·검수 상태: `[-] → [x]`
- 미확정 전문가 기준 유보 표시: `[ ] → [x]`

## 승인 PR 병합 충돌 해결 (2026-10-06)

- 선행 #176/#179 해결 커밋을 포함해 main 변경을 병합했다. CURRENT_STATE의 독립 기록과 모든 Worklog 링크를 보존했다. 코드/Skill 규칙의 충돌은 없었다.
- Python 3.12 경량 CI 환경에서 `python -m pytest backend/tests/test_coaching_skill.py backend/tests/test_prompt_skill_separation.py backend/tests/test_job_search_intent.py -q`: 27 passed. `git diff --check` 통과.
