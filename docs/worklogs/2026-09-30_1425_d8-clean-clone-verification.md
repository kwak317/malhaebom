# Worklog — D8 빈 환경 clean clone 재현 검증

- 일시: 2026-09-30 14:25 KST
- 작업자/에이전트: 사용자 검증, Codex 문서화
- 관련 이슈/PR: `docs/d8-reproducible-runbook` (PR 생성 예정)
- 관련 요구사항/결정: D8 최소 사용자 흐름, README 실행 절차, `/health`

## 1. 목적

기존 개발 checkout과 분리된 빈 clone 환경에서 README의 Docker Compose 실행 절차가 실제 최소 사용자 흐름과 Mock E2E까지 재현되는지 확인하고, 필요한 환경 변수의 범위를 README에 명확히 남긴다.

## 2. 작업 전 상태

- PR #124에 Mock 계약 E2E와 인증 사용자 최소 흐름의 기존 검증 기록은 있었으나, 빈 임시 폴더에서 새 clone한 README 절차를 다시 실행한 증거는 없었다.
- `.env.example`에는 변수 목록이 있었지만, 실제 최소 사용자 흐름과 선택 제공자별 변수의 역할을 README에서 한 번에 확인하기 어려웠다.

## 3. 수행 내용

1. 기존 Compose 서비스를 내리고 Docker Desktop을 재시작했다.
2. `%TEMP%/malhaebom-clean-run`에 새 clone을 만들고 `.env.example`에서 `.env`를 생성했다.
3. 팀 환경의 비밀값을 `.env`에만 설정한 뒤 `docker compose up --build`로 API와 frontend를 기동했다.
4. `GET /health`의 `{"status":"ok"}`와 두 컨테이너의 `healthy` 상태를 확인했다.
5. 브라우저 최소 흐름으로 분석 작업 조회 200, answer revision 저장 201, `/api/agent` 코칭 200을 확인했다.
6. Mock Compose E2E를 실행해 종료 코드 0과 화면·API proxy·MCP 도구·출력 계약 성공을 확인했다.
7. README에 clean clone 절차, 상태 확인, 환경 변수의 필수/선택 범위를 추가했다.
8. D8 health check 항목을 재점검했다. FastAPI `GET /health`는 추론을 실행하지 않고 `{"status":"ok"}`를 반환하며, Compose API healthcheck가 동일 URL을 호출한다.

## 주요 판단과 이유

- `NCS_API_KEY`가 처음 403을 반환했지만 원인은 API에 등록되지 않은 키가 아니라 사용자 입력 오류였다. 올바른 팀 키로 재실행했으므로 저장소 코드·README 실패로 기록하지 않았다.
- 실제 user flow과 Mock E2E는 서로 다른 증거다. 전자는 Supabase·LLM·음성 흐름을, 후자는 고정 계약·Nginx proxy·MCP 도구를 확인한다.
- Vercel/Cloud Run 및 Langfuse 운영 검증은 이번 로컬 clean clone 작업의 범위 밖이므로 완료 처리하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `README.md` | clean clone 실행·health 확인·필수/선택 환경 변수·실제 브라우저 최소 흐름을 명시 |
| `docs/project2-checkpoint-work-cards.md` | D8 로컬 clean clone 실행 절차를 완료로, 운영 환경 차이를 부분 완료로 갱신 |
| `docs/worklogs/2026-09-30_1425_d8-clean-clone-verification.md` | 실제 검증 결과·경계·후속 작업 기록 |

## 5. 검증

```text
새 clone: %TEMP%/malhaebom-clean-run
GET http://localhost:8000/health
결과: {"status":"ok"}

docker compose ps
결과: api와 frontend 모두 healthy

`GET /health` 구현·Compose healthcheck 회귀 확인
결과: `backend/tests/test_mcp_tools.py`가 HTTP 200과 `{"status":"ok"}`를 검증하며,
`docker-compose.yml`의 API healthcheck도 `http://127.0.0.1:8000/health`를 호출

실제 브라우저 최소 흐름 API 로그
결과: GET /analysis-jobs/{job_id} 200,
POST /analysis-jobs/{job_id}/answer-revisions 201,
POST /api/agent 200

docker compose -f docker-compose.yml -f docker-compose.e2e.yml up --build --abort-on-container-exit --exit-code-from coaching-e2e coaching-e2e
결과: 종료 코드 0; screen=ok, api_proxy=ok,
mock_contract=needs_more_info, http_status=200,
mcp_tools=[compare_attempts, get_job_context, get_practice_attempt, get_question]
```

## 6. 발견한 문제 / 남은 리스크

- 로컬 `NCS_API_KEY` 입력 오류는 data.go.kr의 `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`로 나타난다. 키 값은 기록하지 않았다.
- 신규 clone 검증은 팀의 Supabase·OpenRouter·NCS·MCP 비밀값을 안전한 경로에서 제공받는 것을 전제로 한다.

## 미확인 사항

- Vercel/Cloud Run의 외부 URL, CORS, 운영 secret 주입
- 운영 Langfuse Prompt v1 및 trace

## 7. 다음 작업

- D9에서 외부 배포 URL의 health·인증·코칭·MCP 경로를 같은 기준으로 확인한다.
- 배포 환경에서 Langfuse trace와 Prompt production/rollback을 별도 검증한다.
