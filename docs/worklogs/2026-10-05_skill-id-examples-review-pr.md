# I/D 판단 경계 사례 9·10 GitHub 반영 PR

## 목적과 작업 전 상태
사용자가 로컬의 사례 9·10을 PR로 올리고 머지하지 말 것을 요청했다. 원격 main d379c9b에는 사례 1~8만 있었다. 기존 dirty checkout은 보존하고 origin/main 기반의 별도 worktree에서 준비했다.

## 수행과 판단
SKILL.md에 개인 행동과 선택 이유, 관찰 신호와 원인 추론을 구분하는 가상 사례 9·10을 추가했다. 연결된 problem-solving.md의 I/D 판정·근거 범위를 함께 반영했다. 기존 로컬 Spec을 포함했다. Prompt·카탈로그·스키마·UI·운영 설정은 변경하지 않았다.

## 변경 파일
- skills/interview-coach/SKILL.md
- skills/interview-coach/problem-solving.md
- docs/specs/coaching-inference-rationale-evidence.md
- docs/CURRENT_STATE.md
- docs/worklogs/README.md 및 이 기록

## 검증
기존 test-venv에서 PYTHONPATH=backend/tests:backend:.로 test_coaching_skill, test_prompt_skill_separation, test_coaching_prompt 28개 통과. 원격 main 대비 Skill 변경은 사례 9·10 및 I/D 설명 보완에 한정됐다. git diff --check 통과.

## 문제와 미확인
앱 worktree 생성 도구는 부모 작업 공간의 origin/main을 찾지 못해 실패했다. 실제 저장소에서 git worktree add로 분리했다. 실제 LLM 재평가·로그인 E2E·이번 PR을 통한 배포는 수행하지 않았다. 로더·Prompt 테스트는 의미 판정 품질을 증명하지 않는다.

## 다음 작업
PR을 OPEN·비초안·미병합 상태로 생성하고 base/head/파일 범위를 확인한다. merge는 사용자 요청 범위 밖이다.

## 2026-10-06 PR #166 리뷰 피드백 반영

- `docs/CURRENT_STATE.md`의 사례 9·10 절을 `# Current State` 아래로 이동했다.
- 최상위 제목이 첫 줄인지 확인하고, 제목 이동을 제외한 본문 byte 일치와 `git diff --check`를 검증했다.
- I/D 경계 설명·Spec·기존 검증 결과는 변경하지 않았다. 문서 위치 수정이므로 애플리케이션 테스트는 재실행하지 않았다.

## 2026-10-06 사용자 요청에 따른 충돌 해결·머지 준비

- PR #165·#167이 반영된 최신 main과 충돌한 CURRENT_STATE 및 Worklog 목록을 양쪽 기록 보존 방식으로 해결했다.
- 최상위 제목은 첫 줄에 유지한다. Skill 사례 9·10과 I/D 설명은 PR head와 동일하게 보존했다.
- 통합된 작업본에서 Skill 로딩·Prompt 구성 테스트, diff 검사와 PR 크기 정책을 재확인한다.
- 기존 CHANGES_REQUESTED 리뷰의 해소와 최신 CI 상태를 확인한 후 머지한다. 운영 배포·실제 LLM 재평가·로그인 E2E는 수행하지 않는다.
