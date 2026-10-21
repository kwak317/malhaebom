# Worklog — D9 MCP 실패 계약과 gateway 장애 검증

- 일시: 2026-10-01 09:45 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: `test-d9-mcp-failure` 브랜치
- 관련 요구사항/결정: D9 도구 호출 실패 동작 확인, MCP 권한·오류 노출 금지

## 1. 목적

실행 중 MCP gateway 또는 MCP 도구가 실패했을 때 `/api/agent`가 내부 오류를 사용자에게 노출하지 않고, 재시도 가능 여부를 포함한 고정 오류 계약으로 응답하는지 검증한다.

## 2. 작업 전 상태

- MCP stdio gateway의 프로세스 시작 실패, timeout, 도구 오류가 모두 `McpContextGatewayError`로 합쳐졌고 API에서는 `COACHING_PROVIDER_UNAVAILABLE`로 처리됐다.
- API 응답과 관측 결과가 MCP 실패를 provider 오류와 구분하지 못했다.
- 실제 gateway 프로세스 시작 실패를 재현하는 자동 테스트가 없었다.

## 3. 수행 내용

1. `McpContextGatewayError`에 안전한 외부 오류 코드와 `retryable`을 추가했다.
2. MCP timeout, 프로세스/통신 실패, 도구 오류, 잘못된 도구 응답을 구분했다.
3. `/api/agent`가 MCP 오류를 `503`, `mcp_error`, 오류 코드, 재시도 여부로 반환하도록 분리했다.
4. 관측 레코드도 API 응답과 같은 `mcp_error` 상태를 기록하도록 맞췄다.
5. 테스트 전용 `MCP_SERVER_SCRIPT` override를 추가해 존재하지 않는 MCP 서버 경로로 실제 stdio 프로세스 시작 실패를 재현했다. 비어 있으면 기존 `mcp_server/server.py` 경로를 계속 사용한다.

## 주요 판단과 이유

- MCP 문맥을 확보하지 못한 뒤 LLM 호출로 넘어가지 않도록 기존 gateway→service 순서를 유지했다.
- 내부 예외 메시지, token, secret, traceback은 API 응답에 넣지 않았다.
- 외부 API 상태는 `503`으로 유지하되 `mcp_error`로 관측·클라이언트 구분을 가능하게 했다.
- 로그인 사용자 로컬 Compose 검증은 사용자가 직접 수행하고 Network Response와 API 로그로 확인했다. 실제 외부 배포 환경 검증은 별도 범위다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/services/mcp_context_gateway.py` | MCP 오류 코드·재시도 정보와 테스트용 서버 경로 override 추가 |
| `backend/app/schemas/errors.py` | `mcp_error` 실패 상태 추가 |
| `backend/app/main.py` | MCP 오류 API·관측 상태 분리 |
| `backend/tests/test_coaching_api.py` | MCP 오류 계약과 실제 stdio 프로세스 시작 실패 통합 테스트 추가 |
| `docs/worklogs/2026-10-01_0945_d9-mcp-failure-contract.md` | 작업·검증·남은 운영 검증 기록 |

## 5. 검증

```text
.\\venv\\Scripts\\python.exe -m unittest \
  backend.tests.test_coaching_api \
  backend.tests.test_mcp_tools -v

결과: 27 tests, OK

실제 gateway 장애 재현:
MCP_SERVER_SCRIPT에 존재하지 않는 Python 파일을 지정
결과: stdio MCP subprocess 시작 실패 후 POST /api/agent가
503, state=mcp_error, code=COACHING_MCP_UNAVAILABLE, retryable=true 반환

로그인 사용자 Compose 브라우저 검증:
`JOB_SEARCH_PROVIDER=web`으로 공고 선택을 진행하고, `MCP_SERVER_SCRIPT=/app/missing-mcp-server.py`를 API 컨테이너에 주입했다.
답변 revision 저장 201 뒤 `/api/agent`가 두 차례 503을 반환했다.
Chrome Network Response: `state=mcp_error`, `code=COACHING_MCP_UNAVAILABLE`, `retryable=true`.
화면: "코칭 문맥에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."
API 로그: `/app/missing-mcp-server.py` 실행 실패와 `failure_stage=context`, `COACHING_CONTEXT_LOAD_FAILED`를 확인했다.
```

## 6. 발견한 문제 / 남은 리스크

- 로컬 기본 Python에는 `pytest`와 FastAPI가 없었다. workspace `.venv`에 `backend/requirements-ci.txt`를 설치해 `unittest`를 실행했다.
- 외부 배포 환경과 Langfuse Cloud trace 검증은 아직 수행하지 않았다.

## 미확인 사항

- 외부 배포 환경에서 MCP timeout을 강제한 사용자 UI 흐름
- 운영 Langfuse trace에서 `mcp_error`가 표시되는지 여부
- 프런트엔드가 새 `mcp_error` 상태를 별도 문구로 표시하는지 여부

## 7. 다음 작업

- Langfuse trace와 구조화 로그에서 `failure_stage=context`, `mcp_error`가 기록되는지 확인한다.
