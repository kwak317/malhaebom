# Worklog — D6 coaching persistence verifier

- 일시: 2026-09-30 10:15
- 작업자/에이전트: Codex
- 관련 PR: 신규 PR 예정
- 목적: merge된 D6 검증 후속 작업

## 1. 목적

`verify_d6_coaching_completion.py`가 HTTP 200과 terminal status만 확인해 저장 누락을 놓치지 않도록, 동일한 `answer_revision_id`와 `job_snapshot_id`를 가진 `coaching_runs` 행을 직접 조회한다.

## 2. 수행 내용

- `coaching_runs` REST 조회를 추가했다.
- 검증 대상 revision/snapshot과 저장 행의 연결을 확인한다.
- evidence에 `persistence_id`, `persistence_status`를 포함한다.
- 서비스 role key는 출력하지 않으며 `D6_SUPABASE_SERVICE_ROLE_KEY`로만 읽는다.
- 저장 행이 없거나 ID가 불일치하면 검증을 실패시킨다.

## 3. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/tests/verify_d6_coaching_completion.py` | 저장 행 조회·연결 검증 추가 |
| `backend/tests/test_d6_coaching_completion_verifier.py` | 저장 연결 성공/불일치 테스트 추가 |

## 4. 검증

```text
.\.venv\Scripts\python.exe -m unittest backend.tests.test_d6_coaching_completion_verifier -v
Ran 2 tests ... OK

git diff --check
통과
```

실제 사용자 운영 실행은 새 verifier의 `D6_SUPABASE_*` 환경변수를 준비한 뒤 별도로 수행한다. 이 Worklog만으로 운영 저장 검증 완료를 주장하지 않는다.

## 5. 남은 사항

- 실제 운영 환경에서 새 verifier를 실행하고 `persistence_id`를 확보한다.
- MCP request/response payload와 Langfuse trace는 별도 증거 범위다.
