# Worklog — 면접 연습 종료 후 새 연습·홈 이동

- 일시: 2026-09-28 15:20
- 작업자/에이전트: Codex (side conversation)
- 관련 이슈/PR: 생성하지 않음
- 관련 요구사항: 사용자 요청, [Spec](../specs/interview-finish-actions.md)

## 1. 목적

연습 마치기 성공 뒤 요약 안내 아래에서 새 면접과 메인 화면으로 이동한다.

## 2. 작업 전 상태

- 실행 frontend Compose 작업 디렉터리는 `proj2-3-complete-flow`, 포트 18080이다.
- `InterviewFollowUpChat`의 종료 분기는 안내 문구만 표시했다.
- 현재 채팅·선택·답변은 React 메모리이며 `/practice` 새 문서의 `App`은 초기 상태를 만든다. `/`는 `IntroCoachRoomDemo`다.
- 기존 uncommitted 변경이 많아 관련 원본 4개를 임시 경로에 백업했다. 기존 브랜치를 변경하지 않았다.

## 3. 수행 내용

- `finished` 분기에 `/practice`, `/` 일반 링크를 버튼 모양으로 추가했다.
- 보라색 기본 버튼과 흰색 보조 버튼, 줄바꿈·키보드 포커스 스타일을 추가했다.
- 진행 중에는 숨기고 종료 실패에는 기존 재시도를 유지하는 테스트를 확인했다.
- 저장된 기록 삭제가 아닌 현재 UI 세션 초기화로 구현했다. 서버 삭제 API·로그아웃은 호출하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `frontend/src/components/InterviewFollowUpChat.tsx` | 종료 후 이동 링크 2개 |
| `frontend/src/styles/practice-page.css` | 종료 버튼 스타일 |
| `frontend/src/components/InterviewFollowUpChat.test.tsx` | 표시 시점·이동 경로·종료 실패 회귀 검사 |
| `docs/specs/interview-finish-actions.md` | 범위·동작·AC |
| `docs/CURRENT_STATE.md` | 구현과 검증 범위 |
| 이 Worklog | 작업·검증 기록 |

## 5. 검증

- 변경 전 관련 컴포넌트 테스트 7개 통과.
- `npm test -- --run src/components/InterviewFollowUpChat.test.tsx src/components/InlineAttemptComparisonChat.test.tsx src/pages/PracticeConversationFlow.test.tsx`: 3개 파일, 10개 테스트 통과.
- `npm run build`: TypeScript와 Vite production build 통과.
- 백업 대비 최종 변경 검토: 요청한 종료 분기·스타일·테스트만 추가.
- 작업 변경 범위의 공백 검사 통과. 전체 `git diff --check`는 기존 `.github/PULL_REQUEST_TEMPLATE.md` 3·13행의 trailing whitespace 때문에 실패했으며 해당 파일은 수정하지 않았다.
- `agent-browser` CLI 미설치로 CUA 내장 브라우저 사용. 별도 127.0.0.1:18083에서 실제 컴포넌트·App·메인 페이지와 가상 인증/API 응답을 사용했다. 종료 후 두 버튼이 나타나고, 다시 면접하기 클릭 뒤 초기 인사·미선택 공고/질문·비활성 재연습 메뉴를 확인했다. 홈 버튼 클릭 뒤 `/` 메인 화면을 확인했다.
- 개발 확인 화면의 첫 로딩은 가상 인증 모듈의 누락 export로 실패했다. 확인 전용 모듈을 고쳐 재실행했고 제품 코드는 해당 오류로 변경하지 않았다.
- 확인용 파일·스크린샷: 프로젝트 상위 `output/interview-finish-actions-20260928/`, `finished.png`에 두 버튼이 보이는 화면 보관.

## 6. 미확인 사항

- 실행 중인 공유 Docker API/frontend는 변경·재시작·재빌드하지 않았다. 따라서 18080의 정적 자산에는 이번 변경이 아직 반영되지 않았다.
- 실제 사용자 인증·녹음·DB까지 이어지는 E2E, 모바일 뷰포트는 이번에 확인하지 않았다. 새 LLM 호출이나 사용자 DB 삭제/변경을 수행하지 않았다.
- commit/push/PR/merge 없음.

## 7. 다음 작업

후속 반영은 아래 기록을 따른다. 종료 버튼까지의 실제 사용자 전체 연습 E2E는 별도다.

## 8. 후속 사용자 요청 — frontend 재빌드 (15:45)

- 사용자 `재빌드 해줘` 요청으로 frontend만 반영했다.
- `docker compose -p proj2-3-complete-flow config --quiet`: 통과.
- 최초 `up -d --build --no-deps frontend`는 새 자동 스크롤 테스트의 Vitest 미지원 matcher 5곳 때문에 TypeScript 단계에서 실패했다. 기존 컨테이너는 유지됐다.
- 파일을 조사하는 동안 동일 테스트가 호출 횟수·인자 검사로 수정된 상태를 확인했다. 이 side conversation에서는 해당 테스트·hook 소스를 수정하지 않았다.
- 자동 스크롤·면접 후속 채팅·비교·연습 흐름 테스트 4개 파일 15개 통과 후 같은 명령 재시도로 Docker build·frontend 재생성 성공.
- 새 frontend 이미지: `sha256:7f814833ae79a31cf8b108e3caf1b13e77c2ec875651a5e825ddd38936ecdaed`, healthy. 18080의 `/`, `/practice` HTTP 200과 `/assets/index-9fAcTBFL.js`에서 `다시 면접하기`·`홈으로 가기`·`interview-followup-exit-actions`를 확인했다.
- API 컨테이너 ID·이미지·시작 시각은 작업 전후 같고 18000 `/health`는 200/ok다.
- CUA 실제 18080 `/practice` 초기 화면, 로그인 유지·NCS 항목 로딩, 브라우저 error 로그 없음 확인. 녹음·모델 호출·종료까지의 전체 흐름은 재실행하지 않았다.
- 빌드의 단일 JS chunk 500 kB 초과 경고는 비차단 경고이며 요청 범위 밖 최적화를 추가하지 않았다.
