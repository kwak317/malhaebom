# 채팅 내 재녹음·WAV 업로드 흐름 보정 작업 기록

- 일시: 2026-09-22 16:38 KST
- 작업자/에이전트: Codex

## 목표

1차 코칭의 `재녹음 하기`를 누르면 화면을 전환하지 않고, 1차 답변과 같은 채팅 내 녹음 말풍선과 왼쪽 `+` WAV 업로드를 사용할 수 있게 한다. 두 경로 모두 같은 연습 세션·질문을 유지한 `2차 답변`으로 분석한다.

## 구현

- 재녹음용 `InlineChatRecorder`와 WAV 첨부 말풍선을 1차 코칭 결과보다 **아래**에 렌더링하도록 옮겼다. 이전에는 재녹음 UI가 기존 코칭 결과보다 위에 삽입되어, 클릭 후 자동 스크롤이 결과 하단에 머무를 수 있었다.
- 재녹음 시작 안내에 녹음 버튼과 하단 `+` WAV 업로드 경로를 명시했다.
- 재녹음 녹음·WAV 업로드 모두 기존 `retryQuestion`을 재사용하고 `attemptNo=2`로 전송한다. 새 연습 세션을 만들거나 별도 녹음 화면으로 이동하지 않는다.

## 검증

- `npm test -- --run src/pages/PracticeSetupFlow.test.tsx src/pages/PracticeConversationFlow.test.tsx`
  - 2개 파일, 14개 테스트 통과
  - 재녹음 마이크 녹음과 재녹음 WAV 업로드가 각각 `attemptNo=2`로 전달됨을 검증
- `npm run build`: TypeScript 검사와 Vite 프로덕션 빌드 통과
- `docker compose up -d --build frontend`: `localhost:18080` 프런트 컨테이너 재빌드·기동
- agent-browser로 `/practice` 로드, 로그인 전 채팅 입력·WAV 업로드 버튼 렌더링 및 콘솔 오류 없음 확인
