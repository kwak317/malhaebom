# Worklog — 2차 녹음·답변 비교 분석 메뉴

- 일시: 2026-09-22 16:38 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: `docs/specs/second-recording-comparison-menu.md`, `docs/REQUIREMENTS.md` 재연습 비교 요구사항

## 1. 목적

1차 코칭 뒤 같은 질문의 2차 답변을 녹음하고, 2차 코칭 뒤 1·2차 답변 비교 분석으로 이어지는 순서를 사이드바에서 명확히 표시·실행한다.

## 2. 작업 전 상태

- `PracticePage`는 1·2차 분석 결과를 같은 채팅 흐름에 누적하고, 각 코칭 카드의 다음 행동 버튼으로 재녹음 또는 비교 화면 전환을 제공했다.
- 사이드바에는 1~4단계만 있어 2차 녹음과 비교 분석의 이용 가능 시점이 드러나지 않았다.

## 3. 수행 내용

- 코칭 응답이 `ok` 또는 `needs_more_info`로 완료될 때 해당 답변 차수를 상위 채팅 흐름에 알리도록 `CoachingChatMessages`의 선택 콜백을 추가했다.
- 사이드바에 `2차 녹음`, `답변 비교 분석` 메뉴를 추가했다.
- 1차 코칭 완료 전과 2차 코칭 완료 전에는 각각 필요한 메뉴를 비활성화하고, 기존 재녹음·비교 전환 콜백만 호출하도록 했다.
- 메뉴 조건과 코칭 완료 콜백을 프런트엔드 테스트로 확인했다.

## 주요 판단과 이유

- 비교 메뉴는 2차 **분석 완료**가 아니라 2차 **코칭 완료** 뒤에만 활성화했다. 사용자가 1차 코칭을 받고 다시 답한 후, 두 번째 코칭 결과까지 확인한 다음 비교 피드백으로 이동한다는 사용자 흐름과 기존 다음 행동 버튼의 시점을 맞춘 것이다.
- 새 API, DB 변경 또는 비교용 별도 LLM 호출은 추가하지 않았다. 메뉴는 기존 세션·질문·분석 결과 연결을 그대로 사용한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `frontend/src/pages/PracticePage.tsx` | 차수별 코칭 완료 상태와 사이드바 후속 메뉴·활성화 조건을 추가했다. |
| `frontend/src/pages/ResultPage.tsx` | 코칭 성공 시 상위 채팅 흐름으로 완료 콜백을 전달했다. |
| `frontend/src/styles/practice-page.css` | 사이드바 메뉴의 활성·비활성 상태 스타일을 추가했다. |
| `frontend/src/pages/ResultPageFlow.test.tsx` | 코칭 성공 완료 콜백을 검증했다. |
| `frontend/src/pages/PracticeSetupFlow.test.tsx` | 초기 후속 메뉴 비활성 상태를 검증했다. |
| `docs/specs/second-recording-comparison-menu.md` | 기능 Why·Goal·What·How·AC를 기록했다. |
| `docs/CURRENT_STATE.md` | 현재 1·2차 흐름의 UI 진입 조건을 기록했다. |

## 5. 검증

```text
frontend$ npm test -- --run src/pages/ResultPageFlow.test.tsx src/pages/PracticeSetupFlow.test.tsx
2개 테스트 파일, 15개 테스트 통과

frontend$ npm run build
TypeScript 검사와 Vite production build 통과

http://127.0.0.1:5175/practice
사이드바에 두 메뉴가 표시되고, 초기 상태에서 두 메뉴가 비활성화된 것을 접근성 트리로 확인

docker compose up --build -d frontend
프런트엔드 이미지를 재빌드하고 `frontend` 컨테이너를 재생성

http://localhost:18080/practice
재빌드된 컨테이너에서 두 메뉴와 초기 비활성 상태를 접근성 트리로 확인

docker compose ps --format json
api, frontend 컨테이너 모두 healthy 확인
```

## 6. 발견한 문제 / 남은 리스크

- 기존 `ComparisonPage`의 기준별 상태 비교와 증가/동일값 문구는 이번 UI 메뉴 변경 범위에 포함하지 않았다.

## 미확인 사항

- 로그인한 실제 사용자와 외부 코칭 제공자 응답을 포함한 1차 코칭 → 2차 녹음 → 2차 코칭 → 비교 화면 전체 E2E는 실행하지 않았다.

## 7. 다음 작업

- 필요 시 실제 로그인 세션으로 전후 답변 비교의 서버 호환성·기준별 피드백을 E2E 검증한다.
