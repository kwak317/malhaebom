# Worklog — 재답변 비교용 내용 분석 저장

- 일시: 2026-09-22 17:32
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: 1차 코칭 후 재녹음한 답변은 2차 코칭을 표시하지 않고, 1차와의 비교 분석만 제공한다.

## 1. 목적

재답변을 확정한 뒤에도 `내용 변화` 비교가 가능하도록 1차와 같은 기준의 분석 결과를 저장한다. 2차 코칭 결과와 예시 답안은 채팅에 표시하지 않는다.

## 2. 작업 전 상태

1차 전사문 확정 후에는 `/api/agent`를 호출해 `coaching_runs`에 기준별 판정을 저장했지만, 2차는 확정 직후 비교 화면으로 이동했다. 따라서 `PracticeHistoryService`가 비교에 필요한 2차 `content_analysis`를 만들 수 없었다.

## 3. 수행 내용

- 2차 전사문 확정 후 동일 기준의 분석 요청을 실행하도록 수정했다.
- 분석 중에는 `1차 답변과 비교할 내용을 정리하고 있어요` 입력 중 말풍선을 표시한다.
- 분석 응답은 저장만 하고 2차 코칭 결과·예시 답안은 렌더링하지 않는다.
- 분석에 실패하면 비교 분석 재시도 버튼을 제공한다.
- 사이드바 안내를 2차 코칭이 아닌 2차 전사문 확인 기준으로 갱신했다.
- 2차 비교 흐름 테스트를 저장 요청과 비노출 동작까지 검증하도록 갱신했다.

## 주요 판단과 이유

내용 변화 비교에는 1차와 재답변 모두 동일 `criterion_id` 판정이 필요하다. 재답변에 대한 판정 호출은 비교 데이터 준비용으로만 사용하고, 사용자에게는 별도의 2차 코칭으로 보이지 않게 유지했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `frontend/src/pages/ResultPage.tsx` | 2차 확정 뒤 비교용 분석 저장·로딩·재시도 흐름 추가 |
| `frontend/src/pages/ResultPageFlow.test.tsx` | 2차 비교 분석 저장 및 코칭 결과 비노출 회귀 테스트 |
| `frontend/src/pages/PracticePage.tsx` | 재녹음 비교 메뉴 안내 문구를 실제 흐름에 맞게 수정 |
| `frontend/src/pages/PracticeSetupFlow.test.tsx` | 비활성 비교 메뉴 안내 문구 회귀 테스트 |

## 5. 검증

```text
npm test -- --run src/pages/ResultPageFlow.test.tsx src/pages/PracticeConversationFlow.test.tsx src/components/InlineAttemptComparisonChat.test.tsx
3 files / 5 tests passed

npm run build
passed (TypeScript build and Vite production bundle)
```

## 6. 발견한 문제 / 남은 리스크

- 이전에 생성된 연습 기록에는 2차 비교용 분석이 저장되어 있지 않으므로, 해당 기록은 소급 비교할 수 없다.

## 미확인 사항

- 로그인한 실제 사용자 세션에서 LLM 공급자 응답까지 포함한 전체 재녹음 E2E는 이 작업에서 수행하지 않았다.

## 7. 다음 작업

- 새 재녹음 흐름으로 2차 전사문을 확정한 뒤 내용 변화 카드가 표시되는지 사용자 세션에서 확인한다.
