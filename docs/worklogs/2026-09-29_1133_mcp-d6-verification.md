# Worklog — D6 MCP 실행 경로 검증

- 일시: 2026-09-29 11:33 KST
- 작업 브랜치: test/mcp-d6-e2e-safe
- 관련 체크포인트: docs/project2-checkpoint-work-cards.md D6 MCP

## 1. 목적

D6에서 남아 있던 MCP 실행 증거를 프롬프트·Skill 변경과 분리해 먼저 확보한다. 범위는 Agent의 실제 stdio MCP 문맥 조회, HTTP /mcp 권한·ID 경계, 대표 tool request/response, MCP 장애 시 Agent API 응답이다.

## 2. 작업 전 상태

- HTTP /mcp의 initialize, tools/list, 네 도구 호출, Bearer 인증과 사용자 불일치 테스트는 이미 존재했다.
- McpStdioContextGateway가 실제 FastMCP subprocess에서 세 문맥 도구를 읽는 runtime 테스트도 존재했다.
- 다만 POST /api/agent 요청이 실제 stdio MCP 문맥 조회를 거친다는 통합 증거, HTTP MCP의 scope 밖 ID 차단 회귀 테스트, MCP gateway 실패의 API 정규화 테스트가 D6 근거로 명시돼 있지 않았다.

## 3. 수행 내용

1. backend/tests/test_mcp_tools.py
   - HTTP tools/call에서 capability token에 허용되지 않은 question_id=preset-05를 요청하고 MCP tool error로 차단되는 테스트를 추가했다.
2. backend/tests/test_coaching_api.py
   - /api/agent에 테스트 서비스를 주입하되 실제 McpStdioContextGateway를 사용해 get_question, get_practice_attempt, get_job_context를 읽도록 했다.
   - 반환된 MCP 문맥의 question/revision/job ID가 요청과 일치하고 API가 200을 반환하는지 확인했다.
   - McpContextGatewayError 발생 시 API가 HTTP 503, provider_error, COACHING_PROVIDER_UNAVAILABLE, retryable 응답으로 정규화하는지 확인했다.
   - 테스트 파일을 직접 실행해도 프로젝트 루트의 mcp_server를 import할 수 있도록 sys.path 설정을 기존 MCP 테스트와 동일하게 맞췄다.

## 4. 대표 MCP request / response

민감값과 실제 token 원문은 기록하지 않는다.

~~~text
HTTP /mcp
request:
  method: tools/call
  tool: get_question
  arguments:
    context_token: <redacted capability token>
    question_id: preset-04

response:
  HTTP 200
  result.isError: false
  question_id: preset-04
~~~

~~~text
scope 밖 ID 요청:
  tool: get_question
  token-bound question_id: preset-04
  requested question_id: preset-05

response:
  HTTP 200
  result.isError: true
~~~

~~~text
Authorization header 없음:
  POST /mcp
response:
  HTTP 401
~~~

~~~text
Agent 내부 stdio MCP:
  POST /api/agent
  -> get_question
  -> get_practice_attempt
  -> get_job_context
response:
  HTTP 200
~~~

~~~text
MCP gateway 실패:
  McpContextGatewayError
response:
  HTTP 503
  state: provider_error
  code: COACHING_PROVIDER_UNAVAILABLE
  retryable: true
~~~

## 5. 검증

프로젝트 Python runtime proj2-3에서 실행했다.

~~~text
backend/tests/test_mcp_tools.py
Ran 11 tests
OK
~~~

확인 범위:
- HTTP /mcp 네 도구 호출
- Bearer 누락 401
- access token 사용자와 capability token 사용자 불일치 차단
- capability scope 밖 ID 차단
- token 만료·소유권 경계

~~~text
backend/tests/test_coaching_runtime.py
Ran 24 tests
OK
~~~

확인 범위:
- 실제 stdio FastMCP subprocess에서 세 문맥 도구 호출
- coaching runtime 회귀

~~~text
backend/tests/test_coaching_api.py
Ran 12 tests
OK
~~~

확인 범위:
- POST /api/agent -> 실제 stdio MCP 세 문맥 도구 -> 200
- MCP gateway 실패 -> 503 정규화
- 기존 Agent API 오류 계약 회귀

## 6. 발견한 문제 / 미확인 사항

- 테스트 실행 시 Starlette/FastAPI의 deprecation warning이 출력되지만 이번 MCP 검증 실패 원인은 아니며 모든 대상 테스트는 통과했다.
- 테스트용 서명값과 인증 헤더는 새 secret-like 리터럴을 추가하지 않도록 기존 fixture와 런타임 조합값을 재사용한다.
- Gitleaks가 폐기된 PR의 테스트용 고정 문자열 커밋을 전체 이력 스캔에서 계속 탐지해, 해당 폐기 원격 브랜치를 수동 삭제한 뒤 예외 규칙 없이 다시 검증한다.
- 이번 검증은 로컬 fixture와 테스트 인증기를 사용한다. 운영 Supabase JWT와 배포된 /mcp URL의 상호 운용은 별도 운영 검증 범위다.
- 프롬프트·Skill 의미 품질은 이번 MCP 범위에서 변경하거나 재평가하지 않았다. D6 Agent 정상/경계/허위·오염 E2E는 Prompt/Skill 구조 확정 후 수행한다.

## 7. 다음 작업

- Prompt/Skill 구조를 확정한 뒤 D6 Agent 정상·경계·허위/오염 입력 E2E를 실행한다.
- 필요 시 배포 환경에서 실제 Supabase JWT로 HTTP /mcp 상호 운용을 별도 검증한다.

## 리뷰 후 보정

- 로컬 fixture에서 `/api/agent`가 실제 stdio MCP subprocess를 호출하고 HTTP `/mcp`의
  scope·실패 계약을 검증한 사실은 유지한다.
- 다만 fixture 실행만으로 인증 사용자·실제 provider·배포 환경의 "실제 Agent 실행" 증거를
  확보했다고 볼 수 없으므로, D6 MCP 체크포인트 네 항목을 완료(`[x]`)가 아닌 부분 완료(`[-]`)로
  정정했다.
- 대표 request/response는 redacted fixture 기록이며, 운영 credential 또는 실제 사용자 원문은
  기록하지 않았다. 배포 환경에서 안전하게 수집한 증거가 추가되기 전까지 완료 처리하지 않는다.
