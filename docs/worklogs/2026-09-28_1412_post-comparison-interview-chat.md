# Worklog — 비교 후 면접 대화

- 일시: 2026-09-28 14:12 시작
- 작업자: Codex
- 요구: 비교 후 첫 질문 → 짧은 피드백/꼬리질문 → 사용자 질문 우선 답변 → 사용자 종료 요약. PR/merge 금지 유지.
- 실행 checkout: `/Users/kkwakbab/Documents/ChatGPT/2차 프로젝트/proj2-3-complete-flow`, 기존 `codex/team-local-auth-18080` 유지.

## 목적과 범위

기존 1·2차 코칭/비교를 그대로 두고 해당 세션에서 텍스트 면접 대화를 이어간다. 고정 턴 제한을 두지 않는다. 음성 대화, 재채점, RAG, 새 DB schema, 영속 대화 저장, GitHub 작업은 포함하지 않는다. 기존 무제한 에이전트 제외 규칙은 사용자가 요청한 비교 후 세션 대화로만 확장했다.

## 구현

- 인증된 `POST /api/agent/chat`, start/message/finish 계약과 요청 UUID를 추가했다. 서버가 사용자 JWT로 공고·선택 요구사항·최신 확정 답변·코칭과 동일 기준 비교를 조회한다. 클라이언트가 문맥을 주입하지 않는다.
- 세션/작업/revision/코칭의 가장 이른 만료와 소유자, 질문, 기준 버전, revision 변경을 검사한다. 대화 중에도 매 요청 재검사하고 원래 연습 기록은 쓰지 않는다.
- 별도 고정 대화 지침과 Pydantic 출력 검증, 현재 OpenAI-compatible provider를 재사용한다. 최근 메시지 12개와 누적 요약 4000자, 출력 최대 2048토큰으로 제한한다. 모델 응답 본문에는 질문을 쓰지 않고 질문 필드에는 최대 하나만 둔다. 형식 오류는 구체적인 검증 오류로 한 번 재시도한다.
- 비교 성공 뒤 첫 질문을 자동 생성한다. 원래 공고 검색 입력 대신 대화 입력/종료 버튼을 표시하고 짧은 말풍선과 종료 요약을 이어 붙인다. 실패 입력 보존/재시도, 404·409 새 대화 시작, 중첩 메시지 자동 스크롤을 추가했다.
- React StrictMode 시작 요청을 공유하고 최근 성공 요청의 동일 ID 재시도는 같은 응답을 반환한다. 새 시작 ID는 새 대화로 교체한다.
- 관측은 식별자 해시·모델/버전·상태·지연만 사용하고 원문 대화는 기록하지 않는다.

## 변경 파일

- `backend/app/schemas/interview_chat.py`, `backend/app/services/interview_chat.py`, `backend/app/main.py`, `backend/tests/test_interview_chat.py`
- `skills/interview-conversation.md`
- `frontend/src/api/interviewChat.ts`, 해당 API 테스트
- `frontend/src/components/InterviewFollowUpChat.tsx`, 해당 컴포넌트 테스트
- `frontend/src/components/InlineAttemptComparisonChat.tsx`, 해당 테스트
- `frontend/src/pages/PracticePage.tsx`, `frontend/src/hooks/useCoachThreadAutoScroll.ts` 및 테스트, `frontend/src/styles/practice-page.css`
- 본 Worklog, Spec, CURRENT_STATE/ARCHITECTURE/CONSTRAINTS/TARGET_STATE/DECISIONS

## 검증과 수정

- backend 전체 315개 통과: Docker 읽기 전용 소스 bind, 네트워크 차단 환경. 신규 13개는 실제 context repository와 API를 가상 REST/provider로 검증했다. 소유자·만료·삭제·호환 기준·완료 전 차단, 20회 대화/12개 문맥 제한, 실패 보존, 중복 요청, 종료 후 차단을 포함한다.
- frontend 전체 90개 통과, TypeScript 및 production build 통과. 신규 대화/비교/API/스크롤 관련 14개 테스트가 포함된다.
- 읽기 전용 독립 검토에서 복구·멱등성·스크롤·권한 경계를 다시 확인했다. React 검토 지침으로 effect 정리, StrictMode 중복, 입력/버튼 접근성과 상태 범위를 검토했다.
- 실제 모델 첫 호출에서는 본문과 질문 필드에 질문을 중복해 502가 발생했다. 본문 JSON Schema에 물음표 금지 pattern과 정상 예시를 추가하고 repair에 실제 필드 검증 오류를 전달한 뒤 재검증했다.
- 실행 컨테이너의 `google/gemini-3.5-flash-lite`로 네 요청 모두 HTTP 200/출력 검증 통과. 첫 질문은 미보완 원인 판단, 답변에는 피드백과 선택 이유 질문, 사용자 질문에는 먼저 답변, 종료에는 보완한 설명 2개/다음 연습 2개를 반환했다. 테스트 인증/가상 REST 문맥의 API TestClient 검증이며 사용자 DB 저장/관측 전송은 없다.
- Compose API·frontend 재빌드/재기동, 두 컨테이너 healthy, `/health`·`/practice` HTTP 200, `/api/agent/chat` OpenAPI 등록 및 미인증 401을 확인했다.
- 내장 브라우저에서 실제 `/practice` 페이지와 별도 loopback 개발용 컴포넌트 화면을 검증했다. 개발용 화면은 실제 모델의 가상 사례 응답을 재생한다. 입력→피드백→사용자 질문 답변→종료/입력창 제거/요약 표시 확인, 첫 질문·종료 화면 캡처. 실제 연습 페이지 console 오류 없음. 개발용 화면 초기 파일 생성 중 HMR createRoot 경고가 있었으며 production 코드 오류로 판정하지 않았다.

기록: `/tmp/malhaebom-interview-backend-final.log`, `/tmp/malhaebom-interview-frontend-tests.log`, `/tmp/malhaebom-interview-compose-build.log`. 가상 사례 모델 결과/화면은 `/Users/kkwakbab/Documents/ChatGPT/2차 프로젝트/output/interview-chat-20260928/`에 있다. 소스 백업은 `/var/folders/vp/7pp0r4tx0sz43lhc2tmlkmq00000gn/T/malhaebom-interview-chat-before-k6l9gk08`, 기존 이미지는 `malhaebom-api-before-interview-chat:20260928`, `malhaebom-frontend-before-interview-chat:20260928`에 보존했다.

## 제한과 미확인

- 대화는 프로세스 임시 메모리/화면 상태다. 새로고침·재시작·다른 worker에는 복원되지 않는다. 새 대화 버튼으로 재시작한다. 만료 메모리는 요청 시 정리하며 독립 예약 정리 작업은 없다.
- 실제 사용자 로그인·Supabase 기록·녹음부터 이어지는 브라우저 E2E는 수행하지 않았다. 가상 모델 4개 응답과 테스트 통과를 독립 품질 평가/실제 경험 사실 확인으로 확대하지 않는다.
- PR 생성, merge, commit, push는 하지 않았다. 기존 작업 파일을 보존하고 요청 범위의 파일만 변경했다.
- 최종 SHA-256 비교: 기존 461개 중 요청 대상 12개만 변경했고 나머지 449개는 동일하다. 새 파일 10개도 모두 구현·테스트·지침·문서 범위다. 변경 대상 diff/공백 검사 통과.
