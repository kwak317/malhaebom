# Worklog — 연습 화면 대화형 UI 개편

- 일시: 2026-09-22 11:07 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: 기존 공고·요구사항·질문 선택 및 세션 생성 흐름을 유지하면서, 채팅에서 ALIO 검색·원문 분석·요구사항 선택을 연결

## 1. 목적

로그인 후 연습 시작 화면을 화면 전체를 채우는 AI 코치 대화 UI로 보이게 한다. 공고 검색·선택, 요구사항 선택, 질문 선택, 마이크 확인과 세션 생성 동작은 바꾸지 않는다.

## 2. 작업 전 상태

- `PracticePage`는 동일한 기능을 카드 한 장 안에서 단계별로 표시했다.
- 메인 소개 페이지와 `AuthPage`는 별도 화면이며, 이번 요청에서는 유지 대상이다.
- 실행 중인 로컬 프런트엔드는 `proj2-3-complete-flow`의 Docker 컨테이너였지만, 소스가 컨테이너에 bind mount되어 있지 않아 UI 확인은 별도 Vite 개발 서버로 수행했다.

## 3. 수행 내용

- `PracticePage`의 기존 공고·질문 선택 JSX를 그대로 두고, 대화 헤더·코치 메시지·현재 선택 메시지·단계 사이드바·세션 요약 패널로 감쌌다.
- 기존 보라 계열, 폰트, 버튼 색을 유지하면서 넓은 3열 레이아웃과 메시지 버블을 추가했다.
- 모바일에서는 사이드바와 보조 패널을 숨기고 대화 영역만 남기도록 반응형 스타일을 추가했다.
- 채팅에 `개발 관련 공고 보여줘`, `JD 보여줘`를 입력하면 기존 FastAPI ALIO 검색 API를 호출하고, 처음 3개 결과를 선택 카드로 표시하도록 연결했다.
- 선택한 공고는 기존 원문 분석 API로 보내고, 성공하면 근거가 있는 요구사항을 채팅에서 1~2개 선택하게 했다. 이후 기본 질문 시작은 기존 세션 생성·코칭 문맥 경로를 그대로 사용한다.
- 검색·원문 분석 대기 중에는 코치가 입력하는 점 3개 애니메이션을 표시하고, 요청 중 중복 전송을 막았다.
- `COACHING_LLM_MODEL`과 `JOB_REQUIREMENT_ANALYSIS_LLM_MODEL`을 `google/gemini-3.5-flash-lite`로 설정했다. API key는 기존 서버 전용 환경변수를 재사용하며 저장소에 추가하지 않았다.
- 새 프런트 이미지를 `http://localhost:18080`에 반영했다. 호스트 `8000`은 별도 `sentiment-api`가 사용 중이어서, API는 호스트 `18000`·컨테이너 내부 `8000`으로 기동하고 브라우저 진입점은 `18080`으로 유지했다.
- 중앙의 공고 선택 카드는 초기 채팅 화면에서 숨기고, 화면 높이에 맞춘 고정 대화 영역과 하단 메시지 입력창으로 교체했다. 입력한 메시지는 사용자 말풍선으로 전송된다.
- 채팅 결과가 화면보다 길어질 때 마지막 고정 레이아웃 규칙이 `.coach-thread`의 세로 스크롤을 덮어쓴 문제를 수정했다. 페이지 전체는 고정하고 대화 스레드만 세로 스크롤한다.
- 공고 선택 뒤의 분석 중·분석 완료 말풍선은 공고 검색 결과 아래에 렌더링하도록 순서를 분리했다. 검색 완료 안내는 목록 위에 유지한다.
- `google/gemini-3.5-flash-lite`는 OpenRouter 카탈로그에서 JSON Schema를 지원하지만 `provider.require_parameters=true` 조합에는 처리 가능한 경로가 없어 404를 반환했다. `OPENROUTER_REQUIRE_PARAMETERS=false` 환경 설정으로 해당 제한을 끌 수 있게 했고, 서버의 JSON 스키마·Pydantic 검증·원문 근거 검증은 그대로 유지했다.
- 모델이 원문 인용의 띄어쓰기·기호·표현을 조금 바꿔도, 요구사항 핵심 단어가 충분히 겹치는 실제 원문 구간으로 인용을 복원하도록 보완했다. 복원되지 않는 항목은 기존처럼 재시도·차단하며, 화면에는 항상 공고 원문에 존재하는 근거만 보인다.
- 일부 ALIO `srcUrl`은 상세 공고가 아닌 기관 채용 포털 첫 화면이었다. 분석 요청 때 공고 ID와 제목으로 ALIO를 서버에서 다시 조회하고, 응답의 지원자격·우대사항·학력요건·직무분류·결격사유를 우선 분석 원문으로 사용하도록 바꿨다. 상세 페이지는 해당 데이터가 없을 때만 보조 수단으로 남긴다.

## 주요 판단과 이유

- ALIO 키를 LLM이나 브라우저에 주지 않고 FastAPI가 호출하게 했다. 모델은 선택 후의 공고 원문 요구사항 구조화만 담당해 키·권한 경계를 유지한다.
- 화면 높이를 고정한 대화 UI에 맞춰 검색 결과는 먼저 3개만 표시한다. 선택 후에는 기존 요구사항 ID와 세션 생성 계약을 재사용하므로 이후 코칭 컨텍스트가 같은 요구사항을 조회한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `frontend/src/pages/PracticePage.tsx` | 기존 선택 화면을 대화형 코치 레이아웃으로 감싸는 UI 구조 추가 |
| `frontend/src/styles/practice-page.css` | 전체 화면형 채팅 레이아웃, 메시지 버블, 진행 단계, 반응형 스타일 추가 |
| `.env.example`, `.env` | Gemini Flash Lite 공통 모델 설정 |
| `backend/tests/test_alio_requirement_analysis.py` | 공고 원문 분석 모델 설정 회귀 테스트 추가 |
| `docs/specs/chat-alio-job-search.md` | 채팅 검색·선택·분석 계약 추가 |
| `docs/worklogs/2026-09-22_1107_chat-practice-ui.md` | 작업 범위와 검증 기록 |

## 5. 검증

```text
frontend: npm test -- --run src/pages/PracticeSetupFlow.test.tsx
결과: 3 tests passed

frontend: npm run build
결과: TypeScript 검사와 Vite production build 통과

frontend: npm test -- --run src/pages/PracticeSetupFlow.test.tsx
결과: 4 tests passed (기존 공고·질문 흐름 3건과 채팅 입력 전송 1건)

local browser: http://127.0.0.1:4173/practice
결과: 로그인 전 연습 화면에서 전체 화면형 대화 레이아웃, 단계 표시, 코치 메시지, 로그인 CTA가 표시되는 것을 확인

Docker runtime: API_PORT=18000 WEB_PORT=18080 docker compose up -d api frontend
결과: API healthy (18000->8000), frontend healthy (18080->80), /practice=200, 제공 CSS에 coach-chat-page 포함 확인

local browser: http://localhost:18080/practice
결과: 중앙 공고 선택 카드와 스크롤바가 사라진 고정 화면, 하단 입력창, 전송 후 사용자 말풍선 표시 확인

frontend: npm run test -- --run src/api/practiceSetup.test.ts src/pages/PracticeSetupFlow.test.tsx
결과: 2 files, 10 tests passed. 채팅 검색어 변환, 공고 선택, 원문 분석 요청, 요구사항 선택과 대기 말풍선을 포함한다. 분석 완료 말풍선이 공고 목록 다음에 오는 DOM 순서도 검증한다.

frontend: npm run build
결과: TypeScript 검사와 Vite production build 통과

backend container: python -m unittest backend/tests/test_alio_requirement_analysis.py backend/tests/test_practice_setup.py
결과: 13 tests passed. 로컬 Python은 `mcp` 패키지가 없어 같은 테스트를 수집하지 못했으나, 실행 API 컨테이너에서 검증했다.

backend container: python -m unittest backend/tests/test_coaching_runtime.py backend/tests/test_alio_requirement_analysis.py
결과: 12 tests passed. OpenRouter의 엄격한 매개변수 제한 활성화·비활성화 경로와 ALIO 요구사항 설정을 검증했다.

Docker runtime: API_PORT=18000 WEB_PORT=18080 docker compose up -d --build
결과: API와 frontend 이미지를 새로 만들고 컨테이너를 재기동했다. API 모델 환경은 두 항목 모두 `google/gemini-3.5-flash-lite`로 확인했다.

chat scroll regression: `http://localhost:18080/practice`에서 `.coach-thread`의 computed `overflow-y: auto`, `overflow-x: hidden`, `overscroll-behavior: contain`을 확인했다. 로그인된 긴 ALIO 결과의 실제 이동은 사용자 세션에서 별도 확인이 필요하다.

model runtime check: 실행 API 컨테이너에서 `google/gemini-3.5-flash-lite`가 Google 제공 경로로 엄격한 JSON Schema 응답을 반환했다. 실제 요구사항 스키마·원문 근거 검증을 통과한 4개 요구사항도 확인했다.

evidence recovery: API 컨테이너에서 `backend/tests/test_alio_requirement_analysis.py backend/tests/test_coaching_runtime.py`를 실행해 14 tests passed를 확인했다. 실제 ALIO `개발` 검색 결과의 HTTPS 원문 한 건도 분석하여 근거가 있는 요구사항 1개를 생성했다.

official ALIO source: API 컨테이너에서 ALIO 검색·공식 지원자격 원문 추출·요구사항 저장 경로 테스트를 실행해 20 tests passed를 확인했다. 한국교통안전공단 첨단연구개발처 기간제근로자 공고는 공식 원문 2,342자에서 요구사항 3개를 만들었고, 모든 원문 근거가 공식 ALIO 데이터에 존재함을 확인했다.
```

## 6. 발견한 문제 / 남은 리스크

- 개발 환경에 `agent-browser` 실행 파일이 없어 내장 브라우저로 화면을 확인했다.
- 실행 중인 Docker 프런트엔드는 새 소스를 자동 반영하지 않는다. UI 수정 뒤에는 프런트 이미지를 재빌드·재기동해야 한다.
- 실제 ALIO 원문이 JavaScript로만 렌더링되거나 모델 제공자가 응답하지 않으면 분석은 기존 안전한 오류 경로로 끝난다. 공고 원문·요구사항은 분석 제공자에게 전송될 수 있다.
- `OPENROUTER_REQUIRE_PARAMETERS=false`에서는 OpenRouter가 이용 가능한 제공 경로를 선택한다. 응답 계약은 서버가 검증하지만, 제공 경로의 일시적 가용성은 OpenRouter 상태에 영향을 받는다.
- 실제 사용자 로그인 세션의 `/api/alio/recruitments/analyze` 저장 경로는 자동화하지 않았다. 다만 같은 실행 컨테이너에서 ALIO 검색·원문 가져오기·LLM 분석·근거 검증까지 확인했다.
- 원문 상세 페이지와 ALIO 공식 필드가 모두 비어 있는 공고는 가짜 요구사항을 만들지 않고 기존 안전한 오류로 끝난다.

## 미확인 사항

- 실제 로그인 세션 뒤 ALIO 검색·원문 분석까지의 브라우저 E2E는 Google 로그인과 외부 분석 요청 비용을 만들지 않기 위해 자동으로 수행하지 않았다.
- 로그인된 상태의 공고·요구사항·질문 선택 기능 회귀는 단위·컨테이너 테스트로 확인했고, 실제 브라우저 로그인을 통한 수동 E2E는 수행하지 않았다.

## 7. 다음 작업

- 사용자가 실제 로그인한 상태에서 `개발 관련 공고 보여줘`를 입력해 ALIO 원문 접근성과 모델 응답 품질을 확인한다.

## 추가 UI 보완 (2026-09-22)

- 질문 유형을 고르면 코치가 다음 채팅 말풍선으로 `녹음 시작하기` 버튼을 보내도록 변경했다. 질문 선택과 녹음 시작이 같은 카드에 겹치지 않는다.
- 하단 채팅 입력창의 왼쪽에 `+` 버튼을 추가해 WAV 파일을 고를 수 있게 했다. 선택한 파일은 기존 `RecordingPage`의 파일 분석 경로로 전달하므로, 녹음과 WAV 업로드가 동일한 분석·코칭 흐름을 사용한다.
- 녹음 또는 WAV 제출 뒤 `AnalysisPage`에서는 사용자 전송 말풍선 다음에 코치의 `보낸 답변을 분석하고 있어요.` 말풍선과 3점 입력 애니메이션을 표시한다. WAV는 전송 말풍선에 파일 유형을 구분해 표시한다.

### 추가 검증

```text
frontend: npm run test -- --run src/pages/PracticeSetupFlow.test.tsx
결과: 7 tests passed. 질문 유형 선택 뒤 녹음 버튼과 WAV 업로드 전달을 포함한다.

frontend: npm run build
결과: TypeScript 검사와 Vite production build 통과.
```

## 전사 확인·코칭 채팅 전환 (2026-09-22)

- 분석 완료 뒤 결과 화면도 대화형 레이아웃으로 바꿨다. STT 전사문은 코치의 다음 말풍선에서 수정할 수 있고, `전사문 확인`으로 확정한다.
- 전사문 확정과 코칭 요청을 분리했다. 확정 뒤 코치가 `코칭 시작` 버튼을 보내며, 사용자가 선택하면 기존 answer revision·코칭 API를 호출한다.
- 코칭 응답은 근거, 부족 항목, 다음 행동, 예시 답안을 같은 채팅 스레드에 표시한다. 분석 생성, 전사 저장, 코칭 생성 모두 점 3개 코치 입력 중 말풍선을 사용한다.

### 추가 검증

```text
frontend: npm run test -- --run src/pages/ResultPage.test.tsx src/pages/ResultPageFlow.test.tsx src/pages/PracticeSetupFlow.test.tsx
결과: 3 files, 10 tests passed. 수정 전사문 확정, 코칭 요청 중 입력 효과, 코칭 예시 답안 렌더링을 포함한다.

frontend: npm run build
결과: TypeScript 검사와 Vite production build 통과.
```

## 채팅 내 녹음 전환 (2026-09-22)

- 녹음 시작 뒤 별도 `RecordingPage`로 전환하던 경로를 제거했다. 질문 선택과 재녹음 모두 `PracticePage` 채팅 안에서 처리한다.
- 코치가 녹음 버튼을 보내고, 사용자가 누르면 사용자 측 보라색 오디오 말풍선에 녹음 시간·파형·`녹음 끝내기` 버튼이 표시된다. 완료 후에는 오디오 재생, 다시 녹음, 분석 시작을 제공한다.
- WAV 업로드도 즉시 화면을 전환하지 않고 같은 사용자 오디오 말풍선에서 파일 확인 뒤 분석을 시작한다.

### 추가 검증

```text
frontend: npm run test -- --run src/pages/PracticeSetupFlow.test.tsx
결과: 8 tests passed. Fake MediaRecorder로 채팅 녹음 중 상태, 완료 오디오 말풍선, 분석 전달을 검증했다.

frontend: npm run build
결과: TypeScript 검사와 Vite production build 통과.
```
