# D9 MCP 장애 사용자 응답 검증

`backend/tests/verify_d9_mcp_failure.py`는 의도적으로 MCP 문맥 서버를
사용할 수 없게 만든 **로컬 또는 staging 전용** 환경에서 `/api/agent`의
안전한 실패 계약을 확인한다. 운영 환경에서는 실행하지 않는다.

이 절차는 코칭 결과를 확인하는 D6 runner와 달리 다음만 검증한다.

- HTTP `503`
- `detail.state == "mcp_error"`
- `detail.code == "COACHING_MCP_UNAVAILABLE"`
- `detail.retryable == true`
- 사용자에게 표시할 안전한 메시지가 존재함

출력에는 JWT, answer revision ID, job snapshot ID, 사용자 메시지 원문을
포함하지 않는다. `trace_id_present`는 상관관계 확인용 힌트이며 이 verifier의
통과 조건은 아니다.

## 1. 준비

1. 전용 로컬 또는 staging API를 준비한다. 현재 사용 중인 개발 API나 운영
   API를 이 절차에 사용하지 않는다.
2. 로그인 사용자의 **전용 테스트 job**을 하나 준비한다. 검증은 기존 answer
   revision을 수정하지 않지만, 식별자는 실제 소유 범위 안의 값을 사용해야
   한다.
3. JWT와 식별자는 환경 변수로만 설정한다. Git, Worklog, PR 댓글, 채팅에는
   붙여 넣지 않는다.

```powershell
$env:D9_API_BASE_URL = "http://localhost:8000"
$env:D9_ACCESS_TOKEN = "<raw JWT only>"
$env:D9_QUESTION_ID = "preset-04"
$env:D9_ANSWER_REVISION_ID = "<test revision UUID>"
$env:D9_JOB_SNAPSHOT_ID = "<test job snapshot UUID>"
```

`D9_ACCESS_TOKEN`에는 `Bearer ` 접두사를 넣지 않는다.

## 2. MCP 장애를 격리 환경에만 주입

API 컨테이너의 `MCP_SERVER_SCRIPT`를 존재하지 않는 경로로 설정한다. Docker
이미지의 작업 경로가 `/app`이므로 아래 값은 이미지 안에서 의도적으로 없는
파일을 가리킨다.

```powershell
docker compose stop api
docker compose run --rm --service-ports `
  -e MCP_SERVER_SCRIPT=/app/test-fixtures/missing-mcp-server.py `
  api
```

두 번째 명령은 API를 포그라운드에서 실행한다. 이 터미널은 그대로 두고, 새
터미널에서 다음 단계를 실행한다. 정상 API를 멈춘 상태이므로 이 창에서
`Ctrl+C`를 누르기 전까지는 일반 코칭을 수행하지 않는다.

## 3. verifier 실행

새 터미널에서 저장소 루트로 이동한 뒤 실행한다.

```powershell
python backend/tests/verify_d9_mcp_failure.py
```

예상되는 redacted 출력은 다음 형태다.

```json
{"case_id":"d9-mcp-failure-01","http_status":503,"failure_state":"mcp_error","error_code":"COACHING_MCP_UNAVAILABLE","retryable":true,"trace_id_present":true,"user_message_present":true}
```

`trace_id_present`가 `false`여도 API 실패 계약 자체는 통과할 수 있다. 이 경우
API 로그 또는 관측 시스템에서 상관관계 ID 설정을 별도로 확인한다. HTTP 200,
다른 state/code, 또는 `retryable: false`는 실패다.

## 4. 정상 API 복구

MCP 장애 API를 실행한 터미널에서 `Ctrl+C`를 누른 뒤 다음을 실행한다.

```powershell
docker compose up -d api
docker compose ps
```

`api`가 healthy인지 확인한 뒤 일반 코칭을 다시 사용할 수 있다. 테스트가
실패했더라도 이 복구 단계를 생략하지 않는다.
