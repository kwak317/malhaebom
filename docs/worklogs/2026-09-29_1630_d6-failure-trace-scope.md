# Worklog — D6 실패 요청 trace 검증 범위 정리

- 일시: 2026-09-29 16:30 KST
- 작업 브랜치: `d6-real-agent-harness`

## 목적

공고 선택 실패와 Agent 실패를 구분하고, MCP는 팀원 완료 범위로 제외한 뒤 Langfuse 실패 요청 trace 검증에 집중한다.

## 확인 내용

- 브라우저 Network의 503 요청은 `/api/job-search/recommendations/analyze`였다. 이는 공고 검색 provider 실패이며 `/api/agent` 코칭 실패 trace 증거가 아니다.
- `/api/agent` middleware는 응답 상태를 기준으로 `failure_state`를 만들고 observation sink에 기록한다.
- 502/503/504는 각각 schema/provider/timeout 실패로 분류되어 Langfuse sink에서 `ERROR` level로 기록되는 구조다.
- MCP 항목은 팀원 완료 범위로 이번 작업의 독립 검증 대상에서 제외했다.

## 변경 파일

| 파일 | 내용 |
| --- | --- |
| `backend/tests/test_coaching_observability.py` | 실패 observation이 ERROR level·failure_state·redacted output으로 기록되는 계약 테스트 추가 |
| `docs/project2-checkpoint-work-cards.md` | MCP 제외 범위와 Agent/Langfuse 잔여 검증을 명시 |
| `docs/worklogs/2026-09-29_1630_d6-failure-trace-scope.md` | 실패 trace 검증 범위와 UI 503 해석 기록 |

## 미확인

- 실제 Langfuse Cloud/UI에서 provider/schema 실패 observation을 아직 확인하지 못했다.
- 실제 `/api/agent` 요청을 만들려면 공고 선택 문제와 별개로 기존 연습 session의 revision/job snapshot ID가 필요하다.

## 다음 작업

- 실제 `/api/agent` 실패를 의도적으로 발생시킨다(잘못된 provider 설정 또는 schema failure fixture).
- Langfuse에서 `coaching.analyze` trace의 `ERROR`, `failure_state`, prompt/model/latency/retry와 redaction을 확인한다.
