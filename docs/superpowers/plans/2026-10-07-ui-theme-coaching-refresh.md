# UI 테마 및 코칭 화면 새로고침 구현 계획

> **에이전트 작업자용:** 구현 전에 Spec과 설계를 읽고, 각 작업을 테스트 우선 방식으로 진행한다.

**목표:** 기존 코칭·기록 기능을 보존한 채 시작 메인, 지속형 라이트/다크 테마, 녹음/전사 시각 요소를 추가한다.

**아키텍처:** `ThemeProvider`가 UI 전용 테마 선택을 `html[data-theme]`에 적용하고, 의미 기반 CSS token이 화면 색상을 제공한다. 새 메인은 기존 navigation callback만 호출한다. 녹음·전사 상태에는 기존 상태 전이와 API를 바꾸지 않는 마스코트 asset과 표현만 추가한다.

**기술 스택:** React 18, TypeScript, Vite, Vitest, CSS custom property, 투명 PNG asset.

**Spec:** `docs/specs/ui-theme-coaching-refresh.md`; `docs/superpowers/specs/2026-10-07-ui-theme-coaching-refresh-design.md`

## 전역 제약

- 백엔드·DB·API 계약·마이크/STT/코칭 상태 전이·기록 화면 동작을 변경하지 않는다.
- `html[data-theme]`와 의미 기반 CSS token을 사용하고, 라이트/다크 전체 stylesheet를 중복 작성하지 않는다.
- 테마 선택은 브라우저에만 보관하며 Supabase나 API로 보내지 않는다.
- 내 계정 옆 원형 토글에는 다음 전환 동작을 설명하는 접근 가능한 이름과 hover/focus 툴팁을 제공한다.
- 투명 배경 마스코트 PNG 두 장을 새로 생성하며, 제공 스크린샷을 잘라 제품 asset으로 쓰지 않는다.
- 하나의 프런트엔드 PR을 revert하고 직전 Vercel commit을 재배포하면 롤백할 수 있어야 한다.

## 리뷰 중점

- 브라우저 저장소 값이 잘못됐거나 접근할 수 없어도 OS 선호 테마로 안전하게 fallback해야 한다.
- 키보드 focus와 툴팁은 두 테마 모두에서 다음 전환 동작을 식별해야 한다.
- 테마 변경이 기존 기록 조회·삭제·상세 보기 흐름에 영향을 주지 않아야 한다.
- 마이크 거부·녹음 실패·분석 오류 상태는 기존 문구와 행동을 유지해야 한다.
- 이미지 로드 실패에도 읽을 수 있는 녹음/전사 상태 텍스트와 안정적인 레이아웃이 남아야 한다.

---

## 파일 구조

- 생성: `frontend/src/theme/ThemeProvider.tsx`, `ThemeProvider.test.tsx` — 테마 결정·적용·저장과 검증.
- 생성: `frontend/src/components/ThemeToggle.tsx`, `ThemeToggle.test.tsx` — 원형 토글·툴팁과 접근성 검증.
- 생성: `frontend/src/pages/HomePage.tsx`, `HomePage.test.tsx`, `frontend/src/styles/home-page.css` — 새 시작 메인과 이동 검증.
- 생성: `frontend/src/styles/theme.css` — 라이트/다크 token과 focus 스타일.
- 생성: `frontend/src/assets/coach-recording-mascot.png`, `coach-transcribing-mascot.png` — 상태별 투명 asset.
- 수정: `frontend/src/main.tsx`, `App.tsx`, `navigation.tsx` — 테마 전역 적용, 첫 화면, 헤더 토글.
- 수정: `frontend/src/pages/PracticePage.tsx`, `AnalysisPage.tsx`, `styles/practice-page.css` — 녹음/전사 표현만 추가.
- 수정: `frontend/src/App.test.tsx`, `pages/PracticePage.test.ts`, `pages/AnalysisPage.test.ts` — 기존 흐름 회귀 확인.

### 작업 1: 테마 기반과 헤더 토글

**파일:** `frontend/src/theme/ThemeProvider.tsx`, `ThemeProvider.test.tsx`, `components/ThemeToggle.tsx`, `components/ThemeToggle.test.tsx`, `styles/theme.css`, `main.tsx`, `App.tsx`, `navigation.tsx`

**인터페이스:** 전체 앱에서 `ThemeProvider`, `useTheme()`, `ThemeToggle`을 쓴다. `useTheme()`은 `{ theme: "light" | "dark", toggleTheme(): void }`를 제공한다.

- [ ] **1단계: 실패하는 테마·토글 테스트 작성**

OS/default fallback, 유효·무효 저장 값, 저장소 실패, `html[data-theme]`, 다음 동작 `aria-label`, hover/focus 툴팁을 검증한다.

- [ ] **2단계: 테스트 실패 확인**

`frontend/`에서 `npm test -- --run frontend/src/theme/ThemeProvider.test.tsx frontend/src/components/ThemeToggle.test.tsx`를 실행한다. provider와 toggle이 없어 실패해야 한다.

- [ ] **3단계: 테마 provider·token stylesheet·계정 옆 토글 구현**

테마 모듈 소유의 local-storage key를 사용하고 저장소 예외를 처리하며, API 요청 없이 `data-theme`을 적용한다. 표시 툴팁과 focus-visible 스타일을 포함한다.

- [ ] **4단계: 집중 테스트 통과 확인**

2단계 명령을 실행해 PASS를 확인한다.

- [ ] **5단계: 작업 1 커밋**

```bash
git commit -m "feat: add persistent light and dark theme toggle"
```

### 작업 2: 기존 목적지를 바꾸지 않는 시작 메인

**파일:** `frontend/src/pages/HomePage.tsx`, `HomePage.test.tsx`, `styles/home-page.css`, `App.tsx`, `App.test.tsx`

**인터페이스:** `HomePage`는 `onStartPractice(): void`, `onViewHistory(): void`를 받는다. `App`은 home screen만 추가하고 기존 `practice`/`history` 목적지는 유지한다.

- [ ] **1단계: 실패하는 메인 navigation 테스트 작성**

초기 앱 화면에 승인된 두 CTA가 표시되고, `연습하기`가 기존 practice 흐름으로, `기록 확인하기`가 기존 history 흐름으로 이동하는지 검증한다.

- [ ] **2단계: 테스트 실패 확인**

`frontend/`에서 `npm test -- --run frontend/src/pages/HomePage.test.tsx frontend/src/App.test.tsx`를 실행한다. home이 앱 screen이 아니므로 실패해야 한다.

- [ ] **3단계: 시작 메인과 token 기반 CSS 레이아웃 구현**

기존 logo asset과 navigation callback을 사용한다. 안내 카드에는 기능 없는 placeholder 상호작용을 만들지 않는다.

- [ ] **4단계: 집중 테스트 통과 확인**

2단계 명령을 실행해 PASS를 확인한다.

- [ ] **5단계: 작업 2 커밋**

```bash
git commit -m "feat: add coaching start home"
```

### 작업 3: 녹음/전사 시각 asset 생성과 연결

**파일:** `frontend/src/assets/coach-recording-mascot.png`, `coach-transcribing-mascot.png`, `pages/PracticePage.tsx`, `pages/AnalysisPage.tsx`, `styles/practice-page.css`, 해당 테스트.

**인터페이스:** 녹음·분석 상태는 설명적 alt 텍스트를 가진 상태별 `<img>`를 표시한다. 기존 state callback과 API 호출 signature는 유지한다.

- [ ] **1단계: 제공 스크린샷을 스타일 참고로 투명 마스코트 asset 두 장 생성**

마이크·파형이 있는 녹음 asset 하나와 노트북·로딩이 있는 전사 asset 하나를 생성·검토해 `frontend/src/assets/`에 저장한다.

- [ ] **2단계: 실패하는 UI 상태 테스트 작성**

녹음 상태에 녹음 마스코트와 중지 행동이 유지되는지, 활성 분석/전사 상태에 전사 마스코트와 기존 상태 텍스트가 보이는지, alt 텍스트가 있는지 검증한다.

- [ ] **3단계: 테스트 실패 확인**

`frontend/`에서 `npm test -- --run frontend/src/pages/PracticePage.test.ts frontend/src/pages/AnalysisPage.test.ts`를 실행한다. 상태별 image markup이 없어 실패해야 한다.

- [ ] **4단계: 표현 전용 markup과 스타일로 asset 연결**

`MediaRecorder`, `AnswerAnalysisChat` 요청, callback, timer, 오류 처리는 변경하지 않는다. 이미지는 반응형 크기로 표시하고 기존 텍스트·제어 요소를 유지한다.

- [ ] **5단계: 집중 테스트 통과 확인**

3단계 명령을 실행해 PASS를 확인한다.

- [ ] **6단계: 작업 3 커밋**

```bash
git commit -m "feat: add coaching recording and transcription visuals"
```

### 작업 4: 회귀 검증·문서·롤백 기록

**파일:** `docs/CURRENT_STATE.md`, `docs/worklogs/2026-10-07_ui-theme-coaching-refresh-design.md`, 필요 시 `docs/project2-checkpoint-work-cards.md`

- [ ] **1단계: 프런트 회귀 테스트와 production build 실행**

`frontend/`에서 `npm test`, `npm run build`를 실행한다. 모두 exit code 0이어야 한다.

- [ ] **2단계: 데스크톱/작은 화면 수동 확인**

라이트·다크, 키보드 툴팁, 메인 이동, 녹음, 전사, 기록을 확인한다. 권한 있는 배포자가 수행하지 않은 Vercel 배포를 완료로 주장하지 않는다.

- [ ] **3단계: 실제 변경 동작·검증 근거·미해결 사항·롤백 경로 기록**

수행한 근거만 CURRENT_STATE와 Worklog에 기록한다. 관련 없는 checkpoint 상태는 바꾸지 않는다.

- [ ] **4단계: 작업 4 커밋**

```bash
git commit -m "docs: record coaching UI refresh verification"
```

## 계획 자체 점검

- 작업 1~3이 승인된 테마·메인·상태 시각·asset 규칙을 구현하고, 작업 4가 검증·기록·롤백을 다룬다.
- 테마 hook과 메인 callback interface 이름은 후속 작업에서 일관되게 사용한다.
- 리뷰 중점의 위험 다섯 가지는 각각 테스트 또는 회귀 검증 작업으로 다룬다.
- 어느 작업도 백엔드·영속 데이터·코칭 로직·기록 화면 동작을 바꾸지 않는다.
