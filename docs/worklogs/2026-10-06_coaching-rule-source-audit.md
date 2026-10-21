# Worklog — 코칭 판정 기준 단일 기준원 점검

- 일시: 2026-10-06
- 범위: E2E·provider 호출 없이 저장소의 Prompt/Skill/평가 자산 소유권만 정리.

## 목적

프롬프트 설계 체크리스트의 **숫자 기준·판정표 단일 기준원** 항목을 실제 저장소 구조와 맞춰 확정한다.

## 결론

코칭 판정의 canonical source는 `load_skill_bundle()`이 조립하는 versioned Skill bundle 하나다.

- `criteria.json`: criterion ID·버전·검토 상태·기계 판독 계약
- 질문 유형 문서: 유형별 의미·경계 판정·도메인 예시
- `SKILL.md`: 공통 판정 절차·입력 신뢰 경계·근거/사실 보존
- 현재 운영 Prompt: 역할·입력/실행 경계·출력 계약만 소유

## 점검 결과

- canonical Skill에는 제품 판정을 결정하는 고정 숫자 임계값이 없다.
- `700ms`, `350 CPM` 같은 숫자는 평가 입력/회귀 데이터일 수 있지만 제품 판정 기준은 아니다.
- v3/v4/v4.1, 배포 archive, user-supplied v4, reinforced v5는 재현/실험 snapshot이라 판정 규칙을 중복 포함할 수 있다.
- 특히 reinforced v5 candidate는 Boundary table을 포함하므로 새 canonical source로 보지 않고 그대로 production 승격하지 않도록 Spec에 명시했다.
- 다음 승격 후보는 `coaching-v5-skill-owned` 구조로 이관 후 재평가한다.

## 회귀 방지

`backend/tests/test_prompt_skill_separation.py`에 현재 운영 템플릿이 다음 marker를 직접 포함하지 않는 검사를 추가했다.

- Boundary decision table
- threshold_assertion_without_value
- reproducible_test_result
- p95 700ms 예시
- 과거 reproducible/measured outcome 판정 문구

동시에 Skill bundle에 현재 V 규칙, result_verification criterion, team_draft 상태가 포함되는지 확인한다.

## 변경 파일

- `docs/specs/prompt-skill-separation.md`
- `docs/specs/coaching-v5-reinforced-registration.md`
- `backend/tests/test_prompt_skill_separation.py`
- `docs/evidence/coaching-rule-source-audit-2026-10-06.md`
- `docs/CURRENT_STATE.md`
- `docs/worklogs/README.md`
- 이 Worklog

## 체크리스트 영향

- **숫자 기준·판정표를 한곳에서 관리:** 설계/소유권 기준 완료 처리 가능.
- reinforced v5의 실제 production 승격은 별도 release 체크리스트에서 계속 미완료로 둔다.

## 승인 PR 병합 충돌 해결 (2026-10-06)

- 선행 #176 해결 커밋을 포함해 main 변경을 병합했다. CURRENT_STATE의 독립 기록 두 개와 Worklog 인덱스의 모든 링크를 보존했다.
- Python 3.12 경량 CI 환경에서 `python -m pytest backend/tests/test_prompt_skill_separation.py -q`: 15 passed. `git diff --check` 통과.
