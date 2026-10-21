# 코칭 FastAPI·MCP Thin Slice Spec

## Why

- **페르소나**: 선택한 채용공고에 맞춰 프로젝트 문제 해결 경험을 연습하는 신입 백엔드 취업준비생
- **상황**: LLM 모델은 아직 선정되지 않았지만 API 입력, 서버 문맥 조회와 출력 검증은 먼저 고정할 수 있다.
- **문제**:
  1. 브라우저가 답변·공고 원문이나 사용자 ID를 보내면 서버의 검토된 문맥과 다른 데이터로 코칭이 실행될 수 있다.
  2. MCP 조회가 소유자와 만료를 확인하지 않으면 다른 사용자의 연습 기록이 노출될 수 있다.
  3. 모델 연결까지 기다리면 FastAPI·MCP·Pydantic 사이의 계약 오류를 늦게 발견한다.
- **측정 지표**: 모델 없이 인증·문맥 조회·출력 검증 전체 경로를 실행하고 정상·권한·만료·불일치 사례를 자동 테스트한다.

## Goal

- `POST /api/agent`의 `analyze` 요청을 세 개의 서버 ID로 제한한다.
- 서버 소유 mock 문맥과 고정 LLM 형식 출력을 현재 Pydantic 계약으로 검증해 반환한다.
- FastMCP에 `get_question`, `get_practice_attempt`, `get_job_context` 읽기 도구를 구현한다.
- 모든 MCP 도구는 서버 발급 내부 토큰의 사용자·허용 ID·만료와 조회 레코드의 소유자·만료를 확인한다.
- API와 MCP가 같은 `CoachingContextService`를 사용해 검사 규칙이 달라지지 않게 한다.

**성공 기준**: Docker 테스트에서 정상 API 응답, 인증 실패, 알 수 없는·다른 사용자·만료 ID 차단, 세션·질문 불일치 차단, 세 MCP 도구 호출과 내부 토큰 만료 차단이 모두 통과한다.

**Out of Scope**: 실제 LLM API, Supabase 코칭 테이블·migration, MCP HTTP mount와 외부 클라이언트 인증, Langfuse, 프런트엔드 연결, 재답변 비교.

## What

### Happy Path

1. 사용자가 Bearer JWT와 세 ID로 `POST /api/agent`를 요청한다.
2. FastAPI는 JWT에서 사용자 ID를 얻고, 브라우저가 보낸 사용자 ID는 받지 않는다.
3. `CoachingContextService`가 질문·답변 revision·공고 snapshot을 서버 저장소에서 조회한다.
4. 서비스가 답변과 공고 문맥의 소유자·만료·질문·연습 세션 일치를 확인한다.
5. Mock 서비스가 고정 구조의 코칭 출력을 만들고 현재 Pydantic·서버 참조 검증을 실행한다.
6. API가 `status`, `job_alignment`, `intent_assessment`, `criterion_assessments`, `evidence`, `gaps`, `clarifying_question`, `next_actions`를 반환한다.
7. 같은 저장소는 짧은 내부 토큰을 검증한 MCP 읽기 도구에서도 사용된다.

### Edge Cases

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | JWT 없음·만료·검증 실패 | `401 UNAUTHORIZED` |
| EC-02 | 요청에 알 수 없는 필드, 빈 ID, 잘못된 UUID | Pydantic `422` |
| EC-03 | 없는 ID, 다른 사용자 기록, 만료 기록 | 존재 여부를 구분하지 않는 `404 COACHING_CONTEXT_NOT_FOUND` |
| EC-04 | 질문 ID와 답변 revision의 질문이 다름 | `409 COACHING_CONTEXT_CONFLICT` |
| EC-05 | 답변 revision과 공고 snapshot의 연습 세션이 다름 | `409 COACHING_CONTEXT_CONFLICT` |
| EC-06 | 공고 snapshot이 검토 완료 상태가 아님 | `409 COACHING_CONTEXT_CONFLICT` |
| EC-07 | MCP 내부 토큰 만료·서명 오류·허용되지 않은 ID | 도구 실행 전 `McpAccessDenied` |
| EC-08 | Mock 출력의 인용·기준 ID 검증 실패 | `unavailable` 종료 응답, 원시 출력을 노출하지 않음 |

## How

### 사용자 API

```http
POST /api/agent
Authorization: Bearer <Supabase access token>
Content-Type: application/json
```

```json
{
  "action": "analyze",
  "question_id": "preset-04",
  "answer_revision_id": "00000000-0000-0000-0000-000000000101",
  "job_snapshot_id": "00000000-0000-0000-0000-000000000201"
}
```

- `action`은 현재 `analyze`만 허용한다.
- `question_id`는 소문자 영숫자로 시작하고 소문자 영숫자·하이픈만 사용하는 최대 64자 ID다.
- `answer_revision_id`와 `job_snapshot_id`는 UUID다.
- `extra="forbid"`로 `user_id`, 모델·Prompt·도구 이름과 원문 입력을 거부한다.
- 성공 응답은 `CoachingResponse`를 사용한다.

### 서버 문맥

- `QuestionContext`: 질문 ID·본문·질문 유형·활성 기준 ID·기준 버전
- `PracticeAttemptContext`: 사용자·연습 세션·질문·확인된 답변 문장·전달력 지표·만료 시각
- `JobContext`: 사용자·연습 세션·snapshot·선택 요구사항·원문 출처·기준 시각·검토 상태·만료 시각
- Mock 레코드 ID와 문구는 개발 fixture이며 운영 자료로 표시하지 않는다.
- `COACHING_MOCK_ENABLED=true`인 개발 환경에서만 demo 서비스를 만들며 기본값은 `false`다.
- 저장소는 `CoachingContextRepository` 인터페이스로 분리해 나중에 Supabase 구현으로 교체한다.

### MCP 내부 접근

- 내부 토큰은 HS256, 고정 issuer·audience와 최대 5분 TTL을 사용한다.
- claim에는 사용자 ID, 질문 ID, 답변 revision ID, 공고 snapshot ID와 읽기 scope만 넣는다.
- MCP 함수 인수의 ID가 claim의 허용 ID와 일치해야 한다.
- 토큰은 서버 오케스트레이터가 숨은 인수로 전달하며 LLM prompt나 사용자 응답에 넣지 않는다.
- 이번 범위는 stdio FastMCP 도구와 직접 호출 테스트까지다. `/mcp` HTTP mount는 별도 통합 Spec에서 처리한다.

## AC (Given-When-Then)

- **AC-01 · Mock 코칭 성공**
  - GIVEN: 인증 사용자와 서버 demo 문맥의 세 ID가 있다.
  - WHEN: `POST /api/agent`를 호출한다.
  - THEN: `needs_more_info`와 정확한 8개 핵심 필드, 검증된 답변 인용을 반환한다.
- **AC-02 · 요청 경계**
  - GIVEN: 요청에 `user_id` 또는 원문·알 수 없는 필드가 있다.
  - WHEN: 요청을 검증한다.
  - THEN: 코칭 서비스 호출 없이 `422`를 반환한다.
- **AC-03 · 소유자·만료 은닉**
  - GIVEN: 다른 사용자 또는 만료된 답변 revision을 요청한다.
  - WHEN: API와 문맥 서비스를 호출한다.
  - THEN: 두 경우 모두 외부에는 동일한 `404`를 반환한다.
- **AC-04 · 문맥 일관성**
  - GIVEN: 질문 또는 연습 세션이 서로 다른 레코드다.
  - WHEN: 문맥을 조립한다.
  - THEN: 모델·출력 검증 전에 `409`로 차단한다.
- **AC-05 · MCP 질문 조회**
  - GIVEN: 유효한 내부 토큰과 허용 질문 ID가 있다.
  - WHEN: `get_question`을 호출한다.
  - THEN: 고정 질문·유형·활성 기준과 버전을 반환한다.
- **AC-06 · MCP 답변·공고 조회**
  - GIVEN: 유효한 내부 토큰과 소유자·세션·만료가 일치한다.
  - WHEN: `get_practice_attempt`, `get_job_context`를 호출한다.
  - THEN: 현재 답변 문장과 선택 공고 요구사항을 반환한다.
- **AC-07 · MCP 허용 범위**
  - GIVEN: 만료 토큰 또는 토큰과 다른 ID가 있다.
  - WHEN: MCP 도구를 호출한다.
  - THEN: 저장소 조회 전에 접근을 거부한다.
- **AC-08 · Docker 재현**
  - GIVEN: 저장소의 Docker 구성이 있다.
  - WHEN: API 이미지를 빌드하고 백엔드 테스트를 실행한다.
  - THEN: 기존 회귀 테스트와 새 API·MCP 테스트가 모두 통과한다.
