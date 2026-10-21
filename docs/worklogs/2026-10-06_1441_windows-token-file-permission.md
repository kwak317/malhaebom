# Worklog — Windows job-source E2E token-file permission

- 일시: 2026-10-06 14:41 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: E2E 토큰은 로그에 노출하지 않으며, 파일 fallback은 검증 가능한 권한 경계가 있을 때만 사용한다.

## 1. 목적

Windows에서 `.env.job-source-e2e`를 `chmod(0o600)`으로 설정해도 POSIX group/other mode가 반영되지 않아 전체 backend 회귀가 실패하던 문제를 해결한다. 권한을 확인할 수 없는 플랫폼에서 파일 token fallback을 묵인하지 않는 것이 완료 조건이다.

## 2. 작업 전 상태

`backend/tests/test_job_source_e2e_runner.py`의 private token-file 테스트가 Windows에서 실패했다. 임시 파일은 `chmod(0o600)` 전후 모두 `0o666`으로 관찰됐고, `run_job_source_e2e.py`는 `st_mode & 0o077` 검사로 token file을 거부했다.

## 3. 수행 내용

- POSIX mode가 의미 있는 플랫폼에서만 token-file private/public mode 테스트를 실행하도록 분리했다.
- Windows에서 token file이 있더라도 권한을 입증할 수 없음을 명시하고 환경변수 token만 요구하도록 변경했다.
- Windows 전용 회귀 테스트로 명확한 안내 메시지를 고정했다.

## 주요 판단과 이유

Windows에서 POSIX mode 검사를 건너뛰고 token file을 읽으면 inherited ACL로 인한 노출 여부를 확인할 수 없다. 따라서 편의보다 보안 경계를 우선해 Windows에서는 file fallback을 비활성화하고 환경변수 전달을 요구한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/tests/run_job_source_e2e.py` | Windows token-file fallback 차단 및 환경변수 안내 추가 |
| `backend/tests/test_job_source_e2e_runner.py` | OS별 권한 회귀 테스트 분리 |
| `docs/CURRENT_STATE.md` | 현재 동작 기록 |
| `docs/worklogs/2026-10-06_1441_windows-token-file-permission.md` | 작업 기록 |
| `docs/worklogs/README.md` | Worklog 목록 연결 |

## 5. 검증

```text
pytest backend/tests/test_job_source_e2e_runner.py -q
3 passed, 2 skipped
```

실패 재현에서 Windows 임시 파일의 mode가 `0o600` 변경 전후 모두 `0o666`인 것을 확인했다. 전체 backend pytest는 이 환경에서 출력이 약 50% 진행된 뒤 최종 요약 없이 종료되어, 전체 성공으로 주장하지 않는다.

## 6. 발견한 문제 / 남은 리스크

- Windows의 환경변수 전달 방식과 CI secret 주입 권한은 별도 환경 설정에 의존한다.
- Windows ACL을 직접 검사해 token file을 허용하는 기능은 이번 범위에 포함하지 않았다.

## 미확인 사항

- POSIX 환경에서 기존 token-file tests의 실행은 이 Windows 작업 환경에서 수행하지 않았다.

## 7. 다음 작업

- D11 사람 검토 preflight와 D10 증거 수집 runbook을 별도 브랜치에서 진행한다.
