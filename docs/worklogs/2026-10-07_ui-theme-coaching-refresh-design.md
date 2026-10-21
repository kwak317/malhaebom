# Worklog — UI 테마·코칭 화면 새로고침 설계

- 일시: 2026-10-07 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: 사용자 승인으로 시작 메인·코칭 녹음/전사 시각 갱신·라이트/다크 테마를 설계하고, 기록 화면은 유지한다.

## 1. 목적

구현 전 UI 변경 범위, 기존 기능 보존 경계, 이미지 asset 방식과 롤백 경로를 명시한다.

## 2. 작업 전 상태

- `AppHeader`에는 계정 메뉴가 있으나 테마 전환은 없었다.
- 프런트는 React/Vite와 다수의 직접 색상 CSS로 구성돼 있었다.
- 녹음·전사 상태와 기록 화면은 기존 사용자 흐름에 연결돼 있었다.

## 3. 수행 내용

- Why·Goal·What·How·AC 형식의 기능 Spec을 작성했다.
- 테마 토큰/React provider, 새 시작 메인, 녹음·전사 시각 asset, 기록 화면 제외, 롤백을 설계 문서에 고정했다.
- 승인된 설계를 구현 가능한 4개 작업과 테스트·커밋·롤백 단계로 나눈 계획을 작성했다.
- `ThemeProvider`와 계정 메뉴 옆 원형 테마 전환 버튼을 추가해 라이트·다크 선택을 브라우저 저장소에 보존했다.
- `/`의 기본 진입을 새 시작 메인으로 바꾸고, 시작 메인의 연습/기록 CTA를 기존 상태 전환에 연결했다. 기존 기록 화면 구조는 수정하지 않았다.
- 새로 만든 투명 배경 코치 일러스트를 녹음 중과 전사·분석 중 상태에 각각 연결했다.
- 사용자 렌더링 검토에 따라 시작 메인의 질문 카드 본문을 전용 `.home-question-copy` 영역으로 분리하고, 좌측 padding을 70px(모바일 60px)로 늘려 카드 경계선과 글자가 겹치지 않게 했다.
- PR #211 리뷰에서 확인된 미정의 색상 토큰을 기존 semantic token의 alias로 정의하고, 다크 모드에서 시작·연습·기록·계정의 공통 표면·텍스트·입력·코칭 말풍선을 token 기반 색상으로 연결했다.
- 후속 리뷰에서 확인된 전사문 편집기 cascade를 보완했다. 코칭 전사문은 `--text-primary`, 비활성 전사문은 `--text-secondary`와 `--surface-muted`를 사용하도록 더 구체적인 selector로 덮어쓴다.

## 주요 판단과 이유

- 다크 CSS를 화면별로 복제하지 않고 `html[data-theme]`와 semantic token을 사용한다.
- 첨부 스크린샷은 참고용으로만 쓰며, 제품 asset은 투명 배경의 새 이미지로 만든다.
- API·DB·녹음 상태 전이를 바꾸지 않아 UI rollback이 데이터 rollback을 요구하지 않게 한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/specs/ui-theme-coaching-refresh.md` | 기능 Spec |
| `docs/superpowers/specs/2026-10-07-ui-theme-coaching-refresh-design.md` | 구현 전 설계 |
| `docs/superpowers/plans/2026-10-07-ui-theme-coaching-refresh.md` | 구현 계획 |
| `docs/worklogs/2026-10-07_ui-theme-coaching-refresh-design.md` | 작업 기록 |
| `frontend/src/theme/ThemeProvider.tsx` · `frontend/src/components/ThemeToggle.tsx` | 영속 테마 상태와 전환 버튼 |
| `frontend/src/pages/HomePage.tsx` · `frontend/src/styles/home-page.css` | 새 시작 메인 |
| `frontend/src/assets/coach-recording.png` · `frontend/src/assets/coach-transcribing.png` | 녹음·전사 상태용 신규 투명 일러스트 |
| `frontend/src/pages/PracticePage.tsx` · `frontend/src/pages/AnalysisPage.tsx` | 상태별 코치 이미지 연결 |
| `docs/CURRENT_STATE.md` | 실제 프런트 기본 진입 및 UI 상태 반영 |

## 5. 검증

```text
Spec의 Why · Goal · What · How · AC 다섯 섹션 존재 확인
설계 범위가 현재 AppHeader, PracticePage, HistoryPage 구조 및 사용자 승인 범위와 일치하는지 확인
npm test -- --run src/theme/ThemeProvider.test.tsx src/components/ThemeToggle.test.tsx → 3 tests passed
npm test -- --run src/pages/HomePage.test.tsx src/App.test.tsx → 5 tests passed
npm test -- --run src/pages/AnswerAnalysisChat.test.tsx → 2 tests passed
npm test → 34 test files / 180 tests passed
npm run build → passed (기존 번들 크기 경고만 출력)
질문 카드 여백 조정 후 npm test → 34 test files / 181 tests passed
질문 카드 여백 조정 후 npm run build → passed (기존 번들 크기 경고만 출력)
localhost:5173 실제 렌더링에서 질문 본문이 좌측 경계선 안쪽으로 이동한 것을 시각 확인
리뷰 수정 후 npm test → 34 test files / 181 tests passed
리뷰 수정 후 npm run build → passed (기존 번들 크기 경고만 출력)
localhost:5173 다크 모드에서 시작·연습·기록 화면의 카드 표면과 본문 대비를 시각 확인
전사문 편집기 cascade 수정 후 npm test → 34 test files / 181 tests passed
전사문 편집기 cascade 수정 후 npm run build → passed (기존 번들 크기 경고만 출력)
```

## 6. 발견한 문제 / 남은 리스크

- 생성 이미지가 각 약 1.3~1.5 MB라 초기 전송량이 늘어난다. 필요하면 후속 작업에서 WebP/AVIF 변환을 검토한다.
- Vercel 배포와 실제 브라우저의 마이크 권한·녹음 E2E는 이번 로컬 UI 변경에서 재실행하지 않았다.

## 미확인 사항

- 실제 Vercel 배포본에서 모바일 레이아웃과 모든 기존 화면의 다크 모드 대비.

## 7. 다음 작업

- PR 생성 후 팀원 리뷰를 받고, Vercel Preview에서 시작 메인·테마 전환·녹음/전사 화면을 수동 확인한다.
