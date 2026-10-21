# 재녹음 뒤 채팅 내 비교 분석 작업 기록

- 일시: 2026-09-22 17:21 KST
- 작업자/에이전트: Codex

## 확정 흐름

1. 1차 답변 전사문 확인 후 코칭과 예시 답안을 제공한다.
2. 사용자는 코칭을 바탕으로 같은 질문에 재녹음 또는 WAV 파일을 올린다.
3. 2차 답변은 전사문만 확인·수정한다. 2차 코칭이나 예시 답안은 만들지 않는다.
4. `1·2차 답변 비교하기`를 누르면 별도 화면 이동 없이 현재 채팅 하단에서 내용·전달력 비교 결과를 표시한다.

## 구현

- 2차 WAV 또는 녹음 전송 시 `나 · 2차 답변` 말풍선을 1차 코칭 결과 뒤에 추가하고, 왼쪽에는 `1차 답변과 비교하며 분석하고 있어요.` 입력 중 말풍선을 표시한다.
- 2차 전사문 확인 뒤에는 코칭 API를 호출하지 않고 비교 버튼만 표시한다.
- 비교 요청도 사용자 말풍선으로 남기고, 비교 데이터를 읽는 동안 입력 중 말풍선을 보여 준다.
- 비교 결과는 1차·재답변 전사문, 기준별 내용 변화, 전달력 변화만 같은 채팅에 이어서 표시한다.

## 검증

- `npm test -- --run src/components/InlineAttemptComparisonChat.test.tsx src/pages/PracticeConversationFlow.test.tsx src/pages/PracticeSetupFlow.test.tsx src/pages/ResultPageFlow.test.tsx src/pages/AnswerAnalysisChat.test.tsx`
  - 5개 파일, 20개 테스트 통과
  - 2차 전사문 확인 뒤 코칭 호출이 없고 비교 버튼만 표시됨을 검증
  - 비교 데이터를 읽는 동안 입력 중 말풍선, 완료 후 같은 채팅 내 비교 결과 표시를 검증
- `npm run build`: TypeScript 검사와 Vite 프로덕션 빌드 통과
- `docker compose up -d --build frontend`: `localhost:18080` 프런트엔드 재빌드·기동
- agent-browser로 `/practice` 로드 및 콘솔 오류 없음 확인
