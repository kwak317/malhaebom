# 전사 결과 전 분석 입력 중 말풍선 작업 기록

- 일시: 2026-09-22 17:10 KST
- 작업자/에이전트: Codex

## 목표

WAV 파일 또는 채팅 내 녹음을 전송한 뒤, `1차/2차 분석 결과` 전사문 채팅이 나타나기 전까지 코치가 분석 중임을 알려 주는 입력 중 말풍선을 항상 표시한다.

## 구현

- `AnswerAnalysisChat`의 기존 코치 입력 중 말풍선을 분석 요청부터 결과 채팅 추가 전까지 유지한다.
- 백엔드가 즉시 완료를 반환하는 경우에도 최소 450ms 동안 `보낸 답변을 분석하고 있어요.` 말풍선과 점 애니메이션을 표시한다.
- 실제 분석이 더 오래 걸리면 별도 지연을 추가하지 않고, 서버 진행 상태 문구를 계속 표시한다.
- 취소 또는 화면 전환 시에는 대기 후 결과를 추가하지 않도록 기존 `AbortController` 상태를 확인한다.

## 검증

- `npm test -- --run src/pages/PracticeConversationFlow.test.tsx src/pages/PracticeSetupFlow.test.tsx`
  - 2개 파일, 15개 테스트 통과
  - 즉시 완료 응답에서도 결과 전에 `.coach-typing-message`가 표시됨을 검증
- `npm run build`: TypeScript 검사와 Vite 프로덕션 빌드 통과
- `docker compose up -d --build frontend`: 프런트 이미지를 재빌드해 `localhost:18080`에 반영
- `docker compose ps`: API(`18000`)와 frontend(`18080`) 컨테이너 모두 healthy
- agent-browser로 `/practice` 로드 후 화면 렌더링 및 콘솔 오류 없음 확인
