# Worklog — D6 Agent → MCP 운영 검증 스크립트

> 2026-09-30 수정: `/api/agent`는 응답 본문 계약을 바꾸지 않고, redacted
> `X-Trace-Id`와 실제 stdio MCP 도구명만의 `X-MCP-Tools` 헤더를 반환한다.
> 2026-09-30 수정: `/api/agent`의 `CoachingResponse`에는 trace ID, MCP 호출 내역,
> 저장 run ID가 없으므로 verifier는 이를 응답 필드로 요구하지 않는다. 성공 상태만
> 판정하며 MCP·저장·trace 증거는 Langfuse/서버 관측에서 별도로 확인한다.

## 목적

인증된 실제 `/api/agent` 요청의 상태, trace ID, MCP 관련 응답 메타데이터를 민감값 없이 출력해 사용자가 운영 환경에서 재검증할 수 있게 한다.

## 변경 파일

- `backend/tests/verify_d6_agent_mcp_runtime.py`
- `backend/tests/verify_d6_mcp_request_response_evidence.py`

## 실행 방법

```powershell
$env:D6_API_BASE_URL = "https://<api-host>"
$env:D6_ACCESS_TOKEN = "<raw-user-jwt>"
$env:D6_QUESTION_ID = "<question-id>"
$env:D6_ANSWER_REVISION_ID = "<answer-revision-uuid>"
$env:D6_JOB_SNAPSHOT_ID = "<job-snapshot-uuid>"
.\.venv\Scripts\python.exe backend/tests/verify_d6_agent_mcp_runtime.py
```

## 판정

- HTTP 200과 `ok` 또는 `needs_more_info`, opaque trace ID, 세 MCP 도구명을 확인한다.
- HTTP 200과 `ok` 또는 `needs_more_info` 상태를 확인한다.
- 출력에는 사용자 원문·JWT·MCP capability token을 포함하지 않는다.
- 원문·JWT·MCP capability token·tool payload는 헤더와 verifier 출력에 포함하지 않는다.

## 현재 검증

운영 URL과 사용자 JWT가 없어 이 브랜치에서는 실행 증거를 만들지 않았다. 로컬에는 프런트만 실행 중이고 `localhost:8000` API는 직접 노출되지 않았다.

## 다음 작업

이 스크립트를 운영 API에서 실행하고, 같은 trace ID로 Agent → MCP 호출을 확인한다.
