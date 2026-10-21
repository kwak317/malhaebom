# Worklog — 코칭 LLM 실패·MCP HTTP·Langfuse 계측 보강

- 일시: 2026-09-21 09:34 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: PR #17 merge 이후 `feat/llm-mcp-langfuse-hardening` 브랜치, PR 미생성
- 관련 요구사항/결정: `docs/REQUIREMENTS.md`, `docs/CONSTRAINTS.md`, `docs/specs/coaching-runtime-hardening.md`

## 1. 목적

코칭 LLM의 일시 장애와 출력 계약 실패를 제한된 재시도로 처리하고, FastAPI에 인증된 Streamable HTTP `/mcp`를 연결하며, Langfuse에서 실제 provider 호출과 계약 검증 단위를 원문 없이 추적할 수 있게 한다.

완료 조건은 재시도 가능·불가능 오류와 비용 상한, `/mcp` 초기화·도구 목록·세 도구 호출·권한 거부, 요청 trace·generation·validation span 및 개인정보 제외를 자동 테스트로 확인하는 것이다.

## 2. 작업 전 상태

- OpenAI-compatible provider는 timeout·`429`·`5xx`를 즉시 공통 API 오류로 변환했고 전송 재시도나 backoff가 없었다.
- 출력 Pydantic·서버 참조 검증은 최대 2회였지만 provider JSON parse 오류는 보정 재시도 경계 밖이었다.
- FastMCP 세 도구는 구현돼 있었으나 FastAPI 내부 stdio subprocess로만 사용했고 HTTP `/mcp` mount가 없었다.
- Langfuse는 `/api/agent` 요청 종료 시 trace metadata 한 건만 기록했고 실제 provider 호출·재시도·검증 단위를 구분하지 못했다.
- 원래 checkout에는 사용자 미커밋 변경이 있어 최신 `origin/main`의 별도 worktree와 브랜치에서 작업했다.

## 3. 수행 내용

1. LLM 전송 실패 처리
   - timeout·연결 오류·`429`·`5xx`를 최대 1~3회 설정 범위에서 지수 backoff로 재시도했다.
   - `Retry-After`와 지수 backoff를 최대 대기값으로 제한하고 비재시도 `4xx`는 즉시 실패하게 했다.
   - JSON parse 오류를 출력 계약 보정 재시도에 포함하고, provider usage의 누적 비용 상한을 추가했다.
2. Streamable HTTP MCP
   - FastAPI lifespan에서 stateless·JSON FastMCP session manager를 실행하고 `/mcp`에 연결했다.
   - 기존 Supabase/E2E access token verifier를 MCP SDK `TokenVerifier`에 연결했다.
   - HTTP access token subject와 내부 capability token user를 비교하고 기존 scope·ID·만료 검사를 유지했다.
   - root mount 뒤에 등록되던 `/health`가 가려지는 회귀를 발견해 health route를 mount 이전으로 옮겼다.
3. Langfuse 호출 단위 계측
   - 요청별 context trace ID를 만들고 provider HTTP 시도마다 generation을 기록했다.
   - Pydantic·서버 참조 검증마다 validation span을 기록했다.
   - 실제 usage token·cost를 요청 trace에 합산하고 모든 관측 sink 오류를 사용자 응답과 분리했다.
   - generation input/output은 redacted 구조 요약만 사용했다.

## 주요 판단과 이유

- 내부 `/api/agent`의 stdio MCP gateway는 유지했다. HTTP transport 추가와 내부 orchestration 교체를 동시에 하면 장애 범위가 커지므로, 이번에는 외부 `/mcp` 연결과 인증 경계만 추가했다.
- Supabase access token audience는 `authenticated`이므로 MCP SDK의 URL resource 검증은 명시적으로 끄고 기존 JWT issuer·audience 검증기를 재사용했다. 도구 자료 접근은 별도 capability token으로 다시 제한한다.
- Langfuse Prompt Management 게시·rollback과 실제 운영 수신 검증은 배포 전 코드 범위가 아니므로 제외했다.
- 답변·전사·공고·URL·evidence quote·token 원문은 관측 서비스에 보내지 않고 구조 요약과 집계값만 보낸다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `.env.example` | LLM 재시도·비용 상한과 MCP HTTP metadata 설정 예시 |
| `backend/app/main.py`, `backend/main.py` | MCP lifespan/mount, health route 순서, 요청 trace context, usage 집계, 비용 오류 응답 |
| `backend/app/services/coaching_errors.py` | 비용 상한 예외 |
| `backend/app/services/coaching_runtime.py` | 전송/계약 재시도, backoff, usage·비용, generation·validation 계측 |
| `backend/app/services/coaching_observability.py` | trace context, generation/span 계약과 Langfuse sink |
| `mcp_server/server.py` | MCP bearer adapter, HTTP server factory, 이중 사용자 검증 |
| `backend/tests/test_coaching_*.py` | 실패 처리·비용·계측·trace 집계 회귀 테스트 |
| `backend/tests/test_mcp_tools.py` | 실제 `/mcp` initialize/list/call과 인증 테스트 |
| `docs/specs/coaching-runtime-hardening.md` | 구현 전 Spec과 AC |
| `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md` | 현재 구현 경계와 미검증 범위 |

## 5. 검증

```text
docker run --rm -v "$PWD:/app" -w /app malhaebom-current-api:openrouter \
  python -m unittest discover -s backend/tests -p 'test_*.py'
결과: 243 tests, OK
```

```text
HTTP MCP 자동 테스트
- POST /mcp initialize: 200
- tools/list: get_question, get_practice_attempt, get_job_context
- 세 tools/call: 성공
- Authorization 없음: 401
- HTTP 사용자와 capability 사용자 불일치: MCP tool error
```

```text
git diff --check -- 이번 작업 변경 파일
결과: 통과
```

```text
Langfuse 2.60.10 disabled client로 generation/span SDK 호출 smoke
결과: langfuse-sdk-smoke: OK, 네트워크 전송 없음
```

## 6. 발견한 문제 / 남은 리스크

- 실제 OpenRouter/Ollama 장애 응답과 `usage.cost` 형식은 외부 provider 연결에서 추가 확인이 필요하다.
- 운영 Supabase JWT로 `/mcp`를 호출하고 운영 MCP client와 상호 운용한 증거는 아직 없다.
- 실제 Langfuse 서버의 generation/span 수신·화면·flush는 아직 확인하지 않았다.
- HTTP MCP는 FastAPI에 연결됐지만 `/api/agent` 내부는 기존 stdio gateway를 계속 사용한다.
- 작업 시작 시 이미 변경돼 있던 `.github/PULL_REQUEST_TEMPLATE.md`는 이번 작업에서 수정하지 않았다.

## 미확인 사항

- 운영 `MCP_AUTH_ISSUER_URL`, `MCP_RESOURCE_SERVER_URL`과 reverse proxy에서의 Host/Origin 설정
- Langfuse Prompt Management 게시·version 연결·rollback
- 실제 provider 호출 비용 상한 초과와 최종 사용자 응답 E2E

## 7. 다음 작업

- 운영 전 staging에서 실제 Supabase token으로 `/mcp` client 상호 운용을 확인한다.
- Langfuse test project에서 trace-generation-span 연결과 개인정보 제외 payload를 확인한다.
- 필요할 때 내부 stdio gateway를 HTTP client로 교체하는 별도 Spec을 작성한다.
