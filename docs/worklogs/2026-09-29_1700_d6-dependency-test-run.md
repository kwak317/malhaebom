# Worklog — D6 의존성 설치 후 테스트 재실행

- 일시: 2026-09-29 17:00 KST
- 작업 브랜치: `d6-real-agent-harness`
- 관련 PR: #113

## 수행 내용

- `.venv`에 `backend/requirements-eval.txt`와 API/Langfuse/MCP 검증 의존성을 설치했다.
- 전체 backend unittest와 D6 focused suite를 가상환경에서 재실행했다.

## 검증 결과

```text
.\.venv\Scripts\python.exe -m unittest backend.tests.test_coaching_observability backend.tests.test_coaching_runtime backend.tests.test_coaching_api backend.tests.test_mcp_tools -v
결과: 53개 통과
```

```text
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p 'test_*.py'
결과: 507개 실행, 499개 통과, 5 failures, 3 errors
```

## 전체 테스트 잔여 실패 분류

- `test_alio_requirement_analysis` 1건, `test_github_readme_analysis` 1건: 현재 브랜치에 이미 포함된 Prompt 문구 불일치. D6 변경과 무관하며 `PYTHONUTF8=1`에서도 재현됐다.
- `test_playmcp_job_search` 2건: Windows 로컬에서 인증 파일 접근/갱신 fixture가 `PermissionError`로 실패.
- `test_playmcp_job_search` 3건: Windows NTFS에서 POSIX `chmod(0644/0640/0660)` mode를 그대로 재현하지 못해 mode assertion 실패.
- `test_preset_coaching` 1건: Windows 기본 cp949 환경에서 frontend TypeScript UTF-8 파일을 읽어 `UnicodeDecodeError`.

위 실패들은 이번 D6 live harness·failure observation 변경으로 발생한 것이 아니며, PR 설명에 미완료 검증으로 명시한다.

## D6 결론

- 실패 observation 계약은 53개 focused suite에서 통과했다.
- 실제 Langfuse Cloud 실패 trace는 아직 외부 환경 검증이므로 완료 처리하지 않는다.
- 공고 검색 503은 Agent 실패 trace가 아니므로 D6 실패 trace 증거로 사용하지 않는다.

## 리뷰 후 보정

- D6 MCP 체크포인트에 중복으로 들어간 네 항목을 하나의 부분 완료 목록으로 합쳤다.
  각 항목은 fixture/transport 증거와 운영 인증·배포 증거의 미확인 범위를 함께 기록한다.
- live Agent 실행기는 HTTP 200만으로 성공 처리하지 않고,
  `D6_EXPECTED_TERMINAL_STATUS`(기본 `ok`)와 응답 `status`가 일치할 때만 종료 코드 0을 반환하도록 보정했다.
  HTTP 200 + `needs_more_info`가 정상 `ok` 실행으로 기록되지 않는 회귀 테스트를 추가했다.
- Windows NTFS가 POSIX mode를 그대로 보존하지 않아 PlayMCP 인증 파일 테스트가 실패하던 문제는,
  테스트에서 `fstat` 결과를 명시적으로 제어하고 갱신 시 `chmod(..., 0o600)` 호출을 확인하도록 바꿨다.
  배포 Linux의 실제 파일 권한 검사 구현은 변경하지 않았다.
- 분석 Prompt 분리 테스트는 현재 prompt의 완전한 안전 문구를 확인하도록 기대 문자열을 동기화했다.
- `PYTHONUTF8=1`과 프로젝트 `.venv`로 전체 backend unittest를 다시 실행했다.
  이번 실행에서는 D6 live runner의 terminal status 회귀와 Windows 권한 fixture를 포함해
  전체 gate가 종료 코드 0으로 완료됐다.
