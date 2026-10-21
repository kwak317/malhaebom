# Worklog — D6 실제 Agent 실행 하네스

- 일시: 2026-09-29 16:00 KST
- 작업 브랜치: `d6-real-agent-harness`
- 목적: Mock/데모 문맥이 아닌 실제 인증 API를 호출하는 D6 실행기 추가

## 수행 내용

- `backend/tests/run_d6_live_agent_e2e.py`를 추가했다.
- `D6_API_BASE_URL`, `D6_ACCESS_TOKEN`, `D6_QUESTION_ID`, `D6_ANSWER_REVISION_ID`, `D6_JOB_SNAPSHOT_ID`를 받아 실제 `/api/agent`를 호출한다.
- `D6_CASE_ID`로 normal/boundary/injection 등 live evidence case를 구분하며, 미지정 시 기존 호환성을 위해 `d6-normal-live-01`을 사용한다.
- runner 판정은 `D6_CASE_ID`의 case 종류를 `d6_evidence_cases.json`과 연결해 case별 `expected_http_status`와 `expected_terminal_statuses`를 사용한다. normal은 `ok | needs_more_info`를 허용하며, `D6_EXPECTED_TERMINAL_STATUS`를 명시한 경우에만 단일 terminal status로 좁힌다.
- UUID와 raw token 형식을 사전 검증한다.
- 결과는 HTTP 상태·terminal status·trace ID만 출력하고 답변/evidence/source 원문은 출력하지 않는다.

## 검증

```text
python -m unittest backend.tests.test_d6_live_agent_e2e -v
결과: 8개 통과

python -m py_compile backend/tests/run_d6_live_agent_e2e.py
결과: 통과

git diff --check
결과: 통과
```

## 실제 실행 대기

실제 실행에는 인증된 테스트 사용자의 raw Supabase JWT와 해당 사용자의 실제 답변 revision UUID/job snapshot UUID가 필요하다. 이 값은 현재 Codex 프로세스에 전달되지 않았으므로 외부 API 요청은 실행하지 않았다.

```powershell
$env:D6_API_BASE_URL = "http://localhost:8000"
$env:D6_ACCESS_TOKEN = "<raw Supabase access token>"
$env:D6_CASE_ID = "d6-normal-live-01"
$env:D6_QUESTION_ID = "preset-04"
$env:D6_ANSWER_REVISION_ID = "<실제 answer revision UUID>"
$env:D6_JOB_SNAPSHOT_ID = "<실제 job snapshot UUID>"

.\.venv\Scripts\python.exe backend\tests\run_d6_live_agent_e2e.py
```

## 후속 실행 상태

- 실제 로그인 사용자 UI에서 normal/boundary/injection 3종 Agent E2E를 완료했다. 세부 결과는 `2026-09-29_1632_d6-agent-live-e2e.md`에 기록한다.
- 이번 세 건은 브라우저의 실제 인증 흐름으로 수행했으며, live runner 자체를 재호출하지는 않았다.
- 후속 자동화 시 `D6_CASE_ID`를 사용해 각 case의 redacted 결과를 구분할 수 있다.

## 남은 작업

- 현재 UI 수작업을 대체할 answer revision 생성 + Agent 호출 E2E runner 확장
