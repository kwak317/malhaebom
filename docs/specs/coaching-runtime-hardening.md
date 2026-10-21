# 코칭 런타임 실패·MCP HTTP·Langfuse 계측 Spec

## Why

- 현재 LLM provider 호출은 timeout·`429`·`5xx`를 사용자 오류로 변환하지만 전송 재시도와 backoff가 없어 일시 장애를 흡수하지 못한다.
- 현재 FastMCP 도구는 FastAPI가 매 요청 stdio subprocess로만 호출하며, 요구사항에 명시된 외부 Streamable HTTP `/mcp` endpoint가 없다.
- 현재 Langfuse 연동은 요청 종료 시 trace metadata 하나만 기록하므로 실제 LLM 호출·전송 재시도·출력 계약 재시도를 구분할 수 없다.
- 답변·채용공고·모델 원문을 관측 서비스에 저장하면 기존 개인정보·보안 경계를 위반한다.

## Goal

1. 한 계약 시도 안에서 timeout·연결 오류·`429`·`5xx`를 최대 2회까지 지수 backoff로 재시도한다.
2. Pydantic 출력 계약 위반은 기존처럼 보정 prompt로 최대 2회까지 시도하고, 모든 반복 횟수는 상한을 가진다.
3. provider가 보고한 누적 비용이 요청당 설정 상한을 넘으면 추가 LLM 호출을 차단한다.
4. FastAPI에 인증된 Streamable HTTP MCP endpoint를 정확히 `/mcp`에 연결한다.
5. `/mcp`는 사용자 access token과 기존의 짧은 내부 capability token을 모두 검증하고, 두 토큰의 사용자 주체가 다르면 도구 실행을 거부한다.
6. Langfuse에 요청 trace와 각 provider 전송 시도 generation, 각 출력 계약 검증 span을 같은 trace ID로 기록한다.
7. 계측에는 구조·횟수·상태·model·token·cost·latency·버전만 기록하고 원문 답변, 전사, 공고, URL, evidence quote, token은 기록하지 않는다.

**성공 기준**: Docker 테스트에서 재시도 가능/불가능 오류, backoff 상한, 비용 상한, `/mcp` 인증·도구 호출·사용자 불일치, 호출 단위 Langfuse metadata와 민감정보 제외가 모두 통과한다.

**Out of Scope**: 운영 배포, 운영 URL·OAuth metadata 확정, Langfuse 운영 화면 증적, Langfuse Prompt Management 게시·rollback, 다중 provider fallback routing, 새 MCP 도구, 기존 stdio 내부 호출 제거.

## What

### LLM 실패 처리

| 상황 | 처리 |
|---|---|
| timeout·연결 오류 | 같은 계약 시도 안에서 재시도하고 소진 시 `timeout` 또는 `provider_error` |
| `429` | `Retry-After`가 숫자이면 설정된 최대 대기 이내에서 우선 사용, 소진 시 `rate_limited` |
| `5xx` | 지수 backoff 후 재시도, 소진 시 `provider_error` |
| 그 외 `4xx` | 즉시 `provider_error`, 재시도하지 않음 |
| JSON/schema/서버 참조 위반 | 보정 지시를 추가해 계약 재시도, 최종 실패는 `schema_violation` |
| 비용 상한 초과 | 현재 응답은 폐기하고 추가 호출 없이 `COACHING_BUDGET_EXCEEDED` |

- 기본 전송 시도 수는 2회이고 `COACHING_LLM_MAX_TRANSPORT_ATTEMPTS`로 1~3회 범위에서 조정한다.
- backoff 기본값은 0.5초, 최대값은 2초다. 두 값은 환경 변수로 설정하되 음수·역전 값을 거부한다.
- 계약 시도는 기존 최대 2회를 유지한다. 따라서 기본 설정에서 한 사용자 요청은 provider HTTP 호출 최대 4회다.
- 요청 비용 상한 기본값은 USD 0.10이며 provider가 비용을 보고하지 않으면 상한 판정을 보류하고 `cost_usd`를 미확인으로 남긴다.

### Streamable HTTP MCP

- FastAPI는 `/mcp`에 stateless·JSON 응답 모드의 별도 FastMCP app을 mount한다.
- FastAPI lifespan이 FastMCP session manager를 함께 시작·종료한다.
- 외부 MCP 연결은 기존 Supabase JWT 또는 E2E 개발 token 검증기를 재사용한다.
- 각 도구 인수의 `context_token`은 기존 HS256 capability token이며 사용자·scope·허용 ID·만료를 검증한다.
- HTTP access token subject와 capability token user가 다르면 저장소 조회 전에 거부한다.
- FastAPI 내부 코칭 경로는 당분간 기존 stdio gateway를 유지해 변경 범위를 제한한다.

### Langfuse 관측

- trace: 사용자 요청 1건, 이름 `coaching.analyze`.
- generation: 실제 provider HTTP 전송 1회마다 생성한다. 계약 시도 번호, 전송 시도 번호, 재시도 이유, HTTP 상태, model, token, cost, latency, 결과를 metadata로 남긴다.
- validation span: provider가 반환한 JSON을 Pydantic·서버 참조 계약으로 검증할 때마다 생성한다. 계약 시도 번호, 성공 여부, 오류 개수만 남긴다.
- generation input/output에는 원문 대신 `content_policy=redacted`와 message 수·schema 이름·JSON 여부만 기록한다.
- Langfuse 전송 실패는 코칭 API 결과와 재시도 정책을 바꾸지 않는다.

## Edge Cases

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 첫 호출 `500`, 두 번째 성공 | 한 번 backoff 후 성공 반환, 두 generation 기록 |
| EC-02 | 모든 호출 timeout | 시도 상한에서 중단하고 `504 timeout` |
| EC-03 | `429 Retry-After`가 과도하거나 잘못된 값 | 최대 backoff로 제한하거나 지수 backoff 사용 |
| EC-04 | `400` 또는 인증 오류 | 전송 재시도 없이 `503 provider_error` |
| EC-05 | 첫 출력 schema 위반, 보정 출력 성공 | 두 계약 검증 span과 각 provider generation 기록 |
| EC-06 | provider 보고 비용이 요청 상한 초과 | 응답 사용·추가 호출 없이 비용 초과 오류 |
| EC-07 | `/mcp` access token 없음·유효하지 않음 | MCP 인증 단계에서 거부 |
| EC-08 | HTTP 사용자와 capability token 사용자가 다름 | 도구가 저장소 조회 전에 접근 거부 |
| EC-09 | capability token ID·scope·만료 불일치 | 기존과 동일하게 `McpAccessDenied` |
| EC-10 | Langfuse SDK가 예외를 던짐 | 로그만 남기고 API 응답은 유지 |

## How

### 환경 변수

```dotenv
COACHING_LLM_MAX_TRANSPORT_ATTEMPTS=2
COACHING_LLM_BACKOFF_SECONDS=0.5
COACHING_LLM_MAX_BACKOFF_SECONDS=2.0
COACHING_LLM_MAX_COST_USD=0.10
MCP_AUTH_ISSUER_URL=https://<supabase-project>.supabase.co/auth/v1
MCP_RESOURCE_SERVER_URL=http://localhost:8000/mcp
```

- 운영에서는 `MCP_RESOURCE_SERVER_URL`을 실제 HTTPS endpoint로 설정한다.
- 값이 없는 로컬/E2E 환경은 기존 인증 verifier 설정을 기준으로 안전한 로컬 URL을 사용한다.
- secret 값은 로그·trace·응답에 포함하지 않는다.

### HTTP MCP 호출

```text
POST /mcp
Authorization: Bearer <Supabase access token>
Accept: application/json, text/event-stream
```

MCP 초기화 후 `tools/list`, `tools/call`에서 기존 세 도구를 사용한다. 도구 인수에는 서버가 발급한 `context_token`과 해당 ID만 전달한다.

## AC (Given-When-Then)

- **AC-01 · 재시도 성공**
  - GIVEN: 첫 provider 응답이 `500`이고 두 번째가 유효한 JSON이다.
  - WHEN: 코칭 분석을 실행한다.
  - THEN: 설정된 backoff 한 번 후 정상 응답을 반환한다.
- **AC-02 · 최종 실패**
  - GIVEN: timeout·`429`·`5xx`가 시도 상한까지 반복된다.
  - WHEN: 코칭 분석을 실행한다.
  - THEN: 각각 기존 공통 실패 계약으로 끝나고 추가 호출하지 않는다.
- **AC-03 · 비재시도 오류와 비용 상한**
  - GIVEN: 비재시도 `4xx` 또는 비용 상한 초과 응답이다.
  - WHEN: 코칭 분석을 실행한다.
  - THEN: 추가 호출 없이 명시적 오류로 끝난다.
- **AC-04 · 출력 계약 보정**
  - GIVEN: 첫 JSON이 schema 또는 서버 참조 검증에 실패하고 두 번째가 유효하다.
  - WHEN: 분석을 실행한다.
  - THEN: 보정 prompt 1회 후 성공하고 총 호출 상한을 넘지 않는다.
- **AC-05 · `/mcp` 연결**
  - GIVEN: 유효한 사용자 access token과 capability token이다.
  - WHEN: `/mcp`에서 initialize, `tools/list`, 세 `tools/call`을 실행한다.
  - THEN: 기존 세 읽기 도구 결과를 반환한다.
- **AC-06 · MCP 이중 권한 경계**
  - GIVEN: access token이 없거나 두 token의 사용자가 다르거나 capability가 만료됐다.
  - WHEN: `/mcp` 도구를 호출한다.
  - THEN: 저장소 자료를 반환하지 않는다.
- **AC-07 · 호출 단위 계측**
  - GIVEN: 전송 재시도와 출력 계약 재시도가 발생한다.
  - WHEN: 관측 sink를 검사한다.
  - THEN: 실제 전송 수만큼 generation, 검증 수만큼 span이 같은 trace ID로 기록된다.
- **AC-08 · 개인정보 제외와 비차단성**
  - GIVEN: 답변·공고·token이 포함된 요청과 실패하는 Langfuse client다.
  - WHEN: 코칭 분석을 실행한다.
  - THEN: 원문은 관측 payload에 없고 Langfuse 실패가 API 결과를 바꾸지 않는다.
- **AC-09 · 회귀**
  - GIVEN: Docker 테스트 환경이다.
  - WHEN: 전체 backend test suite를 실행한다.
  - THEN: 기존 API·MCP·평가 테스트와 새 테스트가 모두 통과한다.
