# Worklog — D6 인증 사용자 Agent/MCP/저장 경로 검증

- 일시: 2026-09-30 09:30
- 작업자/에이전트: Codex
- 관련 이슈/PR: PR #116, PR #117
- 관련 요구사항/결정: D6 Agent 실제 호출·MCP 호출·실패/부분 완료 상태 증거

## 1. 목적

인증된 로컬 사용자의 음성 분석부터 Agent 호출, MCP 호출, `coaching_runs` 저장까지의 실제 실행 상태를 확인하고 D6 체크포인트에 반영한다.

## 2. 작업 전 상태

- 이전 검증은 `/api/agent` HTTP 200과 `needs_more_info`까지만 확인했다.
- 초기 음성 업로드는 Storage 스키마 문제로 실패했으나, 로컬 Storage 인덱스 보정 후 재검증했다.

## 3. 수행 내용

- 약 47.6초 음성의 `analysis_jobs` 생성 및 완료 상태를 확인했다.
- `answer_revisions`에 확정 전사문과 최신 revision이 생성된 것을 확인했다.
- 최신 revision으로 인증된 `/api/agent` 요청을 실행했다.
- API 로그에서 `CallToolRequest`를 확인해 Agent에서 MCP 호출이 발생했음을 확인했다.
- Supabase `coaching_runs`에서 `needs_more_info` 결과가 저장된 것을 확인했다.

## 주요 판단과 이유

- `needs_more_info`는 HTTP 실패가 아니라 Agent의 유효한 terminal status이므로 저장 성공과 분리해 기록한다.
- API response verifier는 저장 완료를 증명하지 않는다. 이 Worklog의 Supabase SQL 조회는 수동 실행 증거이며 자동 verifier 결과로 표현하지 않는다.
- Langfuse trace, tool payload의 redacted request/response, 권한 오류와 MCP 장애 경로는 담당자 확인 전까지 미완료로 유지한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/project2-checkpoint-work-cards.md` | D6 실제 실행 증거와 남은 검증 범위 반영 |
| `docs/worklogs/2026-09-30_0930_d6-runtime-evidence.md` | 실행·검증 증거 기록 |

## 5. 검증

```text
analysis_jobs SQL 조회
status=completed, completed_at 존재

answer_revisions SQL 조회
confirmed_at 존재, segment_count=8, confirmed_text_length=284

POST /api/agent
HTTP 200, terminal_status=needs_more_info

docker compose logs api
Processing request of type CallToolRequest 확인

coaching_runs SQL 조회
최신 row 생성, status=needs_more_info
```

## 6. 발견한 문제 / 남은 리스크

- 실제 Agent 결과는 `ok`가 아닌 `needs_more_info`였다.
- Langfuse trace는 별도 담당자 확인이 필요하다.
- MCP tool 이름과 redacted request/response payload는 아직 별도 기록하지 않았다.
- 권한 오류/잘못된 ID 차단 및 MCP 장애 시 서비스 동작은 아직 운영 실행 증거가 없다.

## 미확인 사항

- Langfuse UI의 provider, model, token, cost, latency, retry metadata
- managed Prompt production 연결
- MCP 권한 오류와 장애 경로의 운영 증거

## 7. 다음 작업

- Langfuse 담당자가 trace와 provider metadata를 확인한다.
- MCP request/response를 민감값 없이 별도 기록한다.
- 권한 오류와 MCP 장애 시 `needs_more_info`/503 정규화 동작을 각각 실행 검증한다.
