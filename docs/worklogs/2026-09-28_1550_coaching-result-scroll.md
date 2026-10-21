# Worklog — 코칭 완료 후 결과 상단 이동

- 일시: 2026-09-28 15:50 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음; commit/push/PR을 수행하지 않음
- 관련 요구사항/결정: 사용자의 비교 결과 스크린샷, [Spec](../specs/coaching-result-scroll.md)

## 1. 목적

코칭과 답변 비교가 완성되면 채팅의 결과 제목과 답변 카드 시작점이 보이게 한다. 후속 면접 메시지 때문에 다시 하단으로 이동하지 않아야 한다.

## 2. 작업 전 상태

- 대상은 `proj2-3-complete-flow`, 브랜치 `codex/team-local-auth-18080`, 로컬 웹 18080·API 18000이다.
- 공유 스크롤 훅은 `.coach-coaching-result-message`만 결과로 감지했고 `.coach-inline-comparison`은 일반 메시지로 처리했다. 결과 선택도 첫 번째 요소를 사용했다.
- 브라우저에서 실제 비교 컴포넌트는 로딩 말풍선의 DOM 요소를 재사용하며 `class`를 변경했다. 기존 `childList` 관찰만으로 이 완료 전환을 놓쳤다.
- 기존 미커밋 변경은 보존한다. 시작 시 소스 476개 파일 해시와 수정 대상 원본을 `/var/folders/vp/7pp0r4tx0sz43lhc2tmlkmq00000gn/T/malhaebom-coaching-scroll-un8_w8iv`에 백업했다.

## 3. 수행 내용

- Spec을 작성하고 새 회귀 테스트로 하단 이동·예약 취소·첫 결과 선택 문제를 재현했다.
- 공통 훅에서 코칭과 비교를 동일하게 감지하고 최신 결과의 상단으로 이동한다. 새 노드와 `class` 변경을 함께 관찰한다.
- 결과 완료 시 하단 따라가기를 해제한다. 일반 메시지가 예약된 결과 이동을 취소하지 않게 한다. 사용자가 하단으로 돌아오면 일반 채팅 따라가기가 다시 동작한다.
- 임시 Vite 검증 페이지에서 실제 훅·비교 컴포넌트·CSS를 직접 가져왔다. 긴 테스트 답변과 완료 직후 추가되는 후속 메시지로 실제 레이아웃을 검증했다. 검증 페이지는 인증·DB·외부 LLM을 호출하지 않는다.
- 프런트엔드만 로컬 Compose에 재빌드·재생성하고 웹의 실행 번들을 확인했다.
- 최종 검토에서 기존 테스트를 새 파일로 오인한 것을 발견했다. 이전 실행 기록에서 원본을 복구하고 시작 시 SHA-256과 정확히 일치함을 확인했다. 기존 4개 테스트를 보존하고 새 회귀 테스트 6개를 추가해 다시 검증했다.

## 주요 판단과 이유

- API와 컴포넌트 내용 대신 공통 훅을 수정해 PracticePage·ResultPage에서 같은 동작을 사용한다.
- 일반 메시지의 자동 스크롤은 기존처럼 사용자가 하단을 보고 있을 때만 유지한다. DOM 재사용 문제를 포착한 뒤 실제 브라우저 검증을 다시 실행했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `frontend/src/hooks/useCoachThreadAutoScroll.ts` | 비교 완료·클래스 전환 감지, 최신 결과 선택, 결과 이동 보호 |
| `frontend/src/hooks/useCoachThreadAutoScroll.test.tsx` | 기존 4개 테스트 보존, 스크롤 회귀 테스트 6개 추가 |
| `docs/specs/coaching-result-scroll.md` | Why·Goal·What·How·AC |
| `docs/CURRENT_STATE.md` | 현재 동작·검증 범위 기록 |
| 본 Worklog | 수행 내용·근거·미확인 범위 |

## 5. 검증

```text
수정 전 회귀 테스트: 3개 실패, 일반 대화·README 2개 통과
  비교 결과가 top=2000으로 하단 이동
  최신 결과가 아닌 이전 결과 top=626 선택
  후속 메시지가 코칭 상단 이동을 취소해 top=2000으로 이동
수정 후 공유 훅 테스트: 기존 4개 + 신규 6개, 총 10개 통과
npm test: 24개 파일, 97개 테스트 통과
npm run build: TypeScript·Vite 빌드 통과
브라우저: 실제 비교 컴포넌트의 완료 전환 확인
  완료 전 사용자가 채팅 하단에 있음: remaining=-0.5px
  완료 직후 후속 메시지 추가 후: 결과 상단 여백 23.796875px, PASS
  위쪽에서 완료한 경우에도 동일한 여백 확인
  브라우저 error/warn 로그 없음
docker compose up -d --build --no-deps frontend: 성공
http://localhost:18080/practice: 200, 실행 JS index-CV4yU5Hz.js
  비교 결과 selector와 attributeFilter:["class"] 포함
Compose frontend·api: running, healthy
실제 /practice: 연습 화면 렌더링, 브라우저 error/warn 없음
최종 파일 해시·변경 범위·공백 검사: 통과, 기존 4개 테스트 보존 확인
```

- `workspace output/ui/coaching-scroll-20260928/comparison-top.png`의 브라우저 검증 화면은 실제 비교 컴포넌트에 긴 테스트 데이터를 넣은 화면이다. 실제 사용자 코칭 내용의 캡처는 아니다.
- Docker 빌드에는 기존 번들의 500kB 초과 경고가 있었지만 빌드는 성공했다. 이번 작업에 번들 구조 변경은 포함하지 않았다.

## 6. 발견한 문제 / 남은 리스크

- 로딩 말풍선 재사용을 놓치는 문제를 실제 브라우저에서 발견하고 `class` 관찰과 회귀 테스트로 수정했다.
- 브라우저에 이미 열린 연습은 새로고침 전까지 이전 JS로 동작한다. 새로고침하면 현재 메모리의 연습 채팅이 초기화될 수 있다.

## 미확인 사항

- 실제 사용자 녹음·코칭 API·외부 LLM·저장을 포함한 로그인 완주는 재실행하지 않았다. 스크롤 변경은 테스트 데이터의 실제 컴포넌트와 실행 번들로 검증했다.
- `agent-browser` CLI가 없어 CUA 브라우저를 사용했다.
- 시작 시 파일 해시 대비 `docs/worklogs/2026-09-28_1520_interview-finish-actions.md`에도 별도 채팅의 재빌드 기록이 추가돼 있었다. 이 작업에서는 해당 파일을 수정하지 않았고 병행 변경을 유지했다.

## 7. 다음 작업

- 사용자가 새 연습에서 결과 상단을 확인한다. 추가 구현은 없음.

## 8. 최신 main 기준 PR 준비

- 사용자 요청에 따라 최신 `origin/main` `5c495d5`의 별도 checkout에 스크롤 변경만 반영했다. 최신 main의 다른 팀 기능·테스트와 기존 작업 checkout은 보존했다.
- 최신 통합 소스에서 `npm test` 100개와 `npm run build`가 통과했다. 로그인 E2E를 새로 수행한 결과로 표현하지 않는다.
- 중복 Issue 확인 후 [#95](https://github.com/aihuman-7th/proj2-3/issues/95)에 재현과 기대 동작을 기록했다. PR 생성·push는 승인됐으며 merge는 승인되지 않았다.
