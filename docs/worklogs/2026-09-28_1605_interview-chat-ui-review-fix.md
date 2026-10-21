# Worklog — PR #92 대화 시작 불가 안내

- 일시: 2026-09-28 16:05 KST
- 작업자: Codex
- 관련 PR: [#92](https://github.com/aihuman-7th/proj2-3/pull/92)

## 1. 목적
레거시 비교 기록의 start 409를 반복 재시도 오류 대신 정상적인 대화 불가 안내로 처리한다.

## 2. 작업 전 상태
comparison.content_available만으로 start를 요청했고 API가 확정 revision·코칭 run 조건을 거부하면 오류와 재시도 버튼을 계속 보여줬다. start 409 회귀 테스트를 추가해 기존 실패를 확인했다.

## 3. 수행 내용
start 409에 별도 안내 상태를 사용하고 입력 폼·재시도·새 대화 버튼을 표시하지 않는다. 비교 제목과 두 답변은 유지한다. 연결 실패 재시도와 진행 중 대화의 404/409 복구를 유지한다. 선행 #90의 엄격한 호환성 검사에 맞춰 chat API 테스트 데이터에 model/Prompt/실제 criteria 버전만 추가했다.

## 주요 판단과 이유
리뷰가 제시한 409 정상 안내 방식을 선택해 새 서버 준비 상태 필드나 DB 조회를 추가하지 않았다. 실제 API 거부 결과를 사용하며 legacy content_available 자체를 대화 준비의 증거로 삼지 않는다.

## 4. 변경 파일
- `frontend/src/components/InterviewFollowUpChat.tsx`: start 409 안내 상태
- `InterviewFollowUpChat.test.tsx`, `InlineAttemptComparisonChat.test.tsx`: 409·비교 유지·기존 복구 검증
- `backend/tests/test_interview_chat.py`: 선행 PR 통합용 버전 메타데이터
- `docs/specs/interview-chat-unavailable.md`, `post-comparison-interview-chat.md`, `docs/CURRENT_STATE.md`, 이 Worklog

## 5. 검증
- 관련 UI/API client 테스트 13개 통과. start 409와 진행 중 409를 구분하고 비교 카드와 답변 유지, 입력 폼·오류 alert·재시도 부재를 확인한다.
- `npm test`: 24파일·93개 통과.
- `npm run build`: TypeScript·Vite production build 통과.
- #90 수정안과 #92의 API 코드를 별도 복사본에서 함께 적용한 백엔드 전체 468개가 통과했다. 기존 사용자 DB·실행 컨테이너를 사용하거나 변경하지 않았다.

## 6. 발견한 문제 / 남은 리스크
start 409는 대화 준비 조건을 충족하지 못한 상태로 안내한다. 기존 기록의 내용 비교 가능 여부와 대화 시작 가능 여부는 다르다.

## 미확인 사항
실제 로그인·녹음·DB 브라우저 E2E, 운영 배포는 수행하지 않았다. 진행 중인 원래 체크아웃과 컨테이너는 수정하지 않았다.

## 7. 다음 작업
선행 PR부터 검토·통합한다. 이번 요청에서는 머지하지 않는다.
