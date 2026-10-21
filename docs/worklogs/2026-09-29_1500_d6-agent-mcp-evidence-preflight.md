# Worklog — D6 Agent→MCP 증거 하네스 사전 작업

- 일시: 2026-09-29 15:00 KST
- 작업 브랜치: `d6-agent-mcp-evidence`
- 목적: 실제 Agent→MCP 실행 전에 민감정보 없는 증거 포맷과 fixture 테스트를 준비

## 수행 내용

- `build_redacted_evidence()`를 추가해 case ID, HTTP 상태, MCP tool 이름, trace ID, terminal status만 기록하도록 했다.
- 답변 원문과 source URL을 입력해도 결과에 포함되지 않는 회귀 테스트를 추가했다.
- 기존 `compose_coaching_e2e.py`가 redacted evidence helper를 사용할 수 있도록 연결했다.

## 검증

```text
python -m unittest backend.tests.test_d6_evidence_redaction -v
결과: 1개 통과

python -m py_compile backend/tests/compose_coaching_e2e.py backend/tests/d6_evidence_utils.py
결과: 통과

git diff --check
결과: 통과
```

## 사용자 환경에서 필요한 검증

다음 값은 저장소에 기록하거나 공유하지 말고 로컬 `.env`/Compose 환경에서만 설정해야 한다.

```powershell
$env:COACHING_E2E_FRONTEND_URL = "http://localhost:18080"
$env:COACHING_E2E_TOKEN = "<테스트 사용자 JWT>"
python backend/tests/compose_coaching_e2e.py
```

성공 시 JSON 출력에서 `mcp_tools`에 다음 4개가 포함되어야 한다.

```text
get_question
get_practice_attempt
get_job_context
compare_attempts
```

현재 로컬에는 FastAPI/httpx/Pydantic 등 의존성이 설치되지 않았고, 실제 Supabase·MCP·Langfuse 실행 환경도 확인되지 않아 이 단계는 아직 수행하지 않았다.

## 다음 작업

- 사용자가 테스트 토큰과 로컬/배포 대상 URL을 직접 설정한 뒤 Compose 하네스를 실행한다.
- 결과에 실제 trace ID가 없으면 애플리케이션의 response/header 또는 observation sink 연결 지점을 추가로 정한다.
- 이후 `d6-mcp-security-failure` 브랜치에서 잘못된 소유자·ID·timeout 테스트를 진행한다.
