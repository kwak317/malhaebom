# System Prompt 역할·입력·출력·안전 경계 점검 — 2026-10-06

## 결과

서비스 backend의 LLM system Prompt 호출을 다시 inventory한 결과, mutable Prompt는 모두 다음 4개 구획으로 정리했다.

`[역할] → [입력 경계] → [출력 계약] → [안전 경계]`

정리 대상은 README 분석, 공고 요구사항 분석, 비교 후 면접 대화, Skill-owned 코칭 후보, 채용 검색 의도 분류, 질문 rubric 생성·평가·예시 답변 생성이다.

## 남은 예외

현재 배포 v4 코칭 Prompt `prompts/coaching.md`는 10/6 반복평가 및 배포 재현 근거와 연결된 동결 snapshot이다. heading 변경만으로도 Prompt hash가 달라지므로 이번 작업에서 수정하지 않았다.

따라서 현재 체크리스트 판단은 다음과 같다.

- mutable system Prompt 구조: 완료
- 현재 배포 v4 포함 전체 호출 구조 통일: 미완료
- 최종 상태: **부분완료 `[-]` 유지**

완료 조건은 다음 production 후보를 Skill-owned 4섹션 구조로 재평가하고 실제 운영 기본 Prompt를 그 버전으로 전환하는 것이다.

## 비대상

Saramin/JobKorea web-search query는 검색 도구 query이며 LLM system Prompt 호출이 아니므로 이 계약 대상에서 제외했다.
