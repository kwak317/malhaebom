# Worklog — D9 MCP 장애 재검증 절차

- 일시: 2026-10-06 15:00 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: `test/d9-mcp-failure-verification`
- 관련 요구사항/결정: D9 도구 호출 실패 동작 확인, 실패를 재현 가능한 증거로 보존

## 1. 목적

현재 `main`에 이미 병합된 MCP 장애 처리 계약을 변경하지 않고, 전용 local/staging
환경에서 재실행할 수 있는 안전한 검증기와 절차를 추가한다.

완료 조건은 forced MCP 장애 시 verifier가 `503`, `mcp_error`,
`COACHING_MCP_UNAVAILABLE`, `retryable=true`, 사용자용 메시지 존재를 확인하고
민감한 입력값을 출력하지 않는 것이다.

## 2. 작업 전 상태

- `McpStdioContextGateway`는 `MCP_SERVER_SCRIPT` override로 존재하지 않는 MCP
  서버 프로세스 시작 실패를 만들 수 있었다.
- `/api/agent`는 이미 이 실패를 `503`과 `mcp_error`로 정규화했고, 실제 stdio
  시작 실패 단위 통합 테스트도 존재했다.
- D9 실패 흐름을 로그인 사용자 환경에서 다시 실행할 별도 redacted verifier와
  단계별 복구 절차는 없었다.

## 3. 수행 내용

1. `verify_d9_mcp_failure.py`를 추가해 API 실패 응답을 redacted evidence로
   축약하고 고정 실패 계약을 검증하게 했다.
2. verifier가 실패 응답의 내부 메시지, JWT, revision/job ID를 출력하지 않음을
   단위 테스트로 고정했다.
3. 전용 환경에서 `MCP_SERVER_SCRIPT`를 의도적으로 존재하지 않는 경로로 바꾸는
   방법, 실행, 정상 API 복구를 `docs/dev/`에 기록했다.
4. D9 체크포인트 완료 근거에 새 재실행 절차 링크를 추가했다.

## 주요 판단과 이유

- 운영 API나 현재 사용 중인 개발 API를 멈추지 않도록 verifier는 장애를 주입하지
  않고, 이미 격리된 API에만 요청한다.
- 실패 응답은 API의 `detail` 객체에 있으므로 `status`가 아닌 `detail.state`를
  확인한다.
- `X-Trace-Id`는 관측 상관관계에는 유용하지만 API 실패 계약의 필수값으로 두지
  않았다. 헤더 유무가 아니라 안전한 HTTP/JSON 계약이 이 작업의 판정 대상이다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/tests/verify_d9_mcp_failure.py` | redacted MCP 장애 API verifier 추가 |
| `backend/tests/test_d9_mcp_failure_verifier.py` | verifier 출력·거부 조건 단위 테스트 추가 |
| `docs/dev/d9-mcp-failure-e2e.md` | 격리 환경 주입·실행·복구 절차 추가 |
| `docs/project2-checkpoint-work-cards.md` | D9 실패 동작 근거에 재실행 절차 연결 |
| `docs/worklogs/2026-10-06_1500_d9-mcp-failure-reverification.md` | 실제 작업·검증·미확인 사항 기록 |

## 5. 검증

```text
C:\Users\home\Desktop\proj2-3\.venv\Scripts\python.exe -m unittest \
  backend.tests.test_d9_mcp_failure_verifier \
  backend.tests.test_coaching_api \
  backend.tests.test_coaching_diagnostics \
  backend.tests.test_mcp_tools -v

결과: 39 tests, OK
```

그중 `test_agent_returns_safe_503_when_real_mcp_process_cannot_start`는 존재하지
않는 server script를 사용해 실제 stdio subprocess 시작 실패를 재현하고,
`503 / mcp_error / COACHING_MCP_UNAVAILABLE / retryable=true` 계약을 통과했다.

```text
python -m py_compile backend/tests/verify_d9_mcp_failure.py
git diff --check

결과: 성공
```

Docker Desktop을 다시 켠 뒤, 기존 API 의존성 이미지에 새 브랜치 소스를 읽기
전용으로 마운트해 API 회귀 묶음을 컨테이너 안에서 재실행했다. Dockerfile은
STT/TTS용 대형 ML 의존성을 포함하므로, 이 테스트 전용 재검증에서는 이미지
재빌드 대신 소스 마운트를 사용했다.

```text
docker compose -f <isolated-worktree>/docker-compose.yml run --rm --no-deps api \
  -v "<isolated-worktree>:/app:ro" \
  sh -c "test -f /app/backend/tests/verify_d9_mcp_failure.py && \
  python -m unittest backend.tests.test_d9_mcp_failure_verifier \
  backend.tests.test_coaching_api backend.tests.test_coaching_diagnostics \
  backend.tests.test_mcp_tools -q"

결과: 39 tests, OK. 새 verifier 파일을 포함한 새 브랜치 소스가 컨테이너에서
실행됐다.

C:\Users\home\Desktop\proj2-3\.venv\Scripts\python.exe -m unittest \
  backend.tests.test_tracked_artifacts -q

결과: 3 tests, OK. 이 정책 테스트는 `git` 명령을 호출하므로 git이 없는 API
컨테이너가 아니라 호스트에서 분리 실행했다.
```

## 6. 발견한 문제 / 남은 리스크

- 운영 또는 공유 개발 API에 `MCP_SERVER_SCRIPT` 장애를 주입하면 일반 코칭이
  중단되므로, 문서 절차대로 전용 환경에서만 실행해야 한다.

## 미확인 사항

- 격리 Compose API에서 verifier가 실제 JWT/소유자 문맥으로 한 번 통과하는지
- 해당 오류가 외부 배포 환경의 관측 시스템에서 `mcp_error`로 연결되는지

## 7. 다음 작업

- Docker Desktop을 켠 뒤 전용 local/staging API에서 문서의 1~4단계를 실행하고,
  redacted JSON 결과와 API 복구 결과를 별도 Worklog에 기록한다.
