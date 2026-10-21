# Worklog — 코칭 채팅 재답변 버튼

- 일시: 2026-10-06 (KST)
- 작업자: Codex
- 관련 Spec: `../specs/coaching-composer-reanswer.md`
- commit/push/PR/배포: 미수행

## 목적·작업 전 상태
사용자 요청: 보내기 옆 재답변하기 버튼을 누르면 녹음 또는 WAV 업로드를 제공한다. 기존 1차 코칭 뒤에는 재녹음 카드가 자동 표시됐으며 기존 녹음·WAV 구현이 있었다. 작업 전 다수의 미커밋 변경이 있어 관련 4개 파일을 `/tmp/malhaebom-reanswer-button-20261006`에 보관한 뒤 현재 파일에 필요한 변경만 반영했다.

## 수행 내용·주요 판단
- 1차 코칭 완료 후 활성화되는 재답변하기를 보내기 옆에 추가했다.
- 1차 코칭의 자동 재녹음 카드 버튼을 숨기고 재답변 버튼 안내를 표시했다. 독립 결과 화면과 2차 비교 카드는 유지한다.
- 버튼을 누르면 기존 같은 질문의 2차 녹음 패널을 열며 패널에 WAV 파일 올리기를 추가했다.
- 1차 완료 뒤 첫 녹음 패널이 다시 나타나는 조건을 막았다. 버튼을 누르기 전에는 WAV 업로드도 막아 1차 답변으로 잘못 재제출되지 않게 했다.
- 재답변 진행 중 중복 시작을 비활성화하고 2차 완료 후 버튼을 숨긴다. 기존 공고 변경·세션 초기화 동작을 유지한다.
- 모바일은 입력칸 아래에 보내기·재답변하기를 나란히 배치했다.
- 별도 배포 기준 작업 폴더의 대화 Prompt·Skill도 버튼 클릭 흐름과 일치하도록 안내를 수정했다. 해당 파일을 기존 로컬 Prompt에 복사하지 않았다.

## 변경 파일
- `frontend/src/pages/PracticePage.tsx`
- `frontend/src/pages/ResultPage.tsx`
- `frontend/src/pages/PracticeConversationFlow.test.tsx`
- `frontend/src/styles/practice-page.css`
- `docs/specs/coaching-composer-reanswer.md`
- `docs/CURRENT_STATE.md`, 이 Worklog
- 저장소 밖 후보: `../proj2-3-deployed-prompt-update-20261005/source/prompts/preparation-conversation-v1.md`, `skills/preparation-conversation/SKILL.md`

## 검증
- 관련 3개 파일 28 tests 통과. 활성 조건, 버튼 인접 배치, 자동 카드 제거, WAV 파일 선택 호출, MP3 거절, 같은 세션 재사용, 중복 시작 비활성 및 2차 완료 후 숨김 검증.
- `npm test -- --run`: 29 test files, 140 tests 통과.
- 기본 `npm run build`는 기존 `node_modules/@types/* 2` 중복 타입 디렉터리로 TS2688 실패. 원본 의존성은 수정하지 않았다.
- `node node_modules/typescript/bin/tsc -p tsconfig.app.json --types react,react-dom,node`: 통과.
- `node node_modules/typescript/bin/tsc -p tsconfig.node.json --types node`: 통과.
- `node node_modules/vite/bin/vite.js build --outDir /tmp/malhaebom-reanswer-vite-dist-20261006`: 통과.
- Playwright + 설치된 Chrome, 가상 API/auth fixture로 실제 수정 React 컴포넌트 확인. 준비 단계는 DOM 이벤트로 설정한 합성 UI 검사이며 로그인 사용자 E2E가 아니다. 1440×1000·390×844 화면, page error 0, 모바일 composer 가로 넘침 없음, 버튼으로 녹음 패널 표시 및 WAV filechooser·첨부 카드 연결 확인.
- 증거: 저장소 밖 `../output/coaching-reanswer-button-20261006/{verification.json,desktop.png,mobile.png,mobile-upload.png}`.
- 수정 전 사본과 이번 diff를 대조했고 관련 코드 `git diff --check` 통과.

## 발견한 문제·미확인 사항
보내기 버튼은 현재 공고 검색 API를 사용한다. 앞서 만든 자유 대화 후보를 3.5에 연결하는 코칭 채팅 서버/API는 아직 구현·등록되지 않았다. 실제 마이크·STT·LLM 호출, 로그인 사용자 E2E, 운영 화면 및 배포는 이번에 검증하지 않았다.

## 다음 작업
코칭 대화 API 및 화면 메시지 연결을 별도 구현하고 실제 로그인 흐름을 검증한다. 운영 반영은 별도 배포 승인 범위에서 수행한다.

## GitHub PR 분리 검증 (2026-10-06)
GitHub main의 UI에 재답변 변경만 이식했다. 기존 로컬 Worklog 위 검증은 과거 증거다. 이번 체크아웃의 frontend 전체 105 tests, 표시 플래그 분리 검사 3 tests, TypeScript/Vite build 통과. 새 대화 API 연결은 별도 서버 PR이다.

## 대화 API 연결
준비·1차 코칭 채팅을 별도 preparation API로 연결한다. 답변/질문을 분리해 표시하고 경력 정리를 같은 준비 대화에 유지한 뒤 세션 생성 때 bind한다. 명시적 공고/JD 요청은 기존 검색 흐름을 유지한다. 새 hook의 진행·실패·세션 연결·늦은 응답 무시 5 tests 및 전체 111 tests, build 통과. 실제 API는 runtime PR 배포가 선행되어야 한다.
