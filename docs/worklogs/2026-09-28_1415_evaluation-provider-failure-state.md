# Worklog — 평가 provider 실패 상태 재현 안정화

- 일시: 2026-09-28 14:15 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 평가 실행 회귀 수정 PR은 본 커밋 후 생성
- 관련 요구사항/결정: `AGENTS.md` 5절(평가 오염 방지), 7절(기존 테스트 우선), 8절(Worklog)

## 1. 목적

격리된 provider 호출 실패가 `provider_error`로 기록되는지 검증하는 테스트가 Windows 실행 환경에서 `timeout`으로 불안정하게 실패하는 원인을 확인하고, 테스트 의도에 맞는 안정적인 시간 예산으로 수정한다.

## 2. 작업 전 상태

- 전체 backend unittest discovery는 445건 중 `test_isolated_provider_failure_returns_without_cost` 1 failure와 `tzdata` 부재 관련 37 errors를 보였다.
- 해당 테스트는 연결 불가 주소(`127.0.0.1:1`)의 OpenAI-compatible runner에 `timeout_seconds=1`을 설정하면서 `provider_error`를 기대했다.

## 3. 수행 내용

1. 대상 테스트만 실행해 7건 중 해당 1건이 `timeout`으로 재현됨을 확인했다.
2. 자식 프로세스 시작과 provider 요청의 대기 경계를 조사했다. 1초 제한에서는 provider 오류를 자식이 부모에 전달하기 전에 hard timeout이 먼저 발생할 수 있었다.
3. 같은 연결 불가 provider fixture의 시간 제한을 5초로 조정했다. 이는 provider 오류 분류를 검증할 시간을 주지만, 실제 연결 실패 시 즉시 반환되므로 테스트가 5초를 항상 소비하지는 않는다.
4. 불필요한 runtime handshake 실험 코드는 제거하고 테스트 fixture 변경만 남겼다.

## 주요 판단과 이유

- `timeout` 자체는 지정된 제한 안에 결과를 전달하지 못한 호출에 대해 올바른 분류다. 1초짜리 fixture가 `provider_error`를 요구한 것이 불안정성의 원인이었다.
- 제품의 hard timeout 정책이나 failure-state 분류 로직은 바꾸지 않았다. 목표는 provider 오류를 확인하는 테스트가 의도와 다른 timeout 경합에 의존하지 않게 하는 것이다.
- 이전 실행의 `tzdata` 오류 37건은 현재 환경에서는 재현되지 않았다. 이 작업에서는 의존성 구조를 변경하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/tests/test_evaluation_records.py` | 격리 provider 오류 fixture의 timeout을 1초에서 5초로 조정 |
| `docs/worklogs/2026-09-28_1415_evaluation-provider-failure-state.md` | 재현·판단·검증 결과 기록 |

## 5. 검증

```text
실행 환경: 프로젝트 루트 .venv + PYTHONPATH=<project root>

수정 전:
.venv\Scripts\python.exe -m unittest backend.tests.test_evaluation_records -q
결과: 7 tests 중 1 failure. expected `provider_error`, actual `timeout`.

수정 후:
.venv\Scripts\python.exe -m unittest backend.tests.test_evaluation_records -q
결과: 7 tests, OK

.venv\Scripts\python.exe -m unittest discover -s backend/tests -p 'test_*.py' -q
결과: 443 tests, OK (exit code 0)
```

## 6. 발견한 문제 / 남은 리스크

- 실제 provider가 지정된 제한 안에 응답·오류를 돌려주지 못하면 계속 `timeout`으로 기록된다. 이는 이 테스트가 검사하는 즉시 연결 실패와 다른 정상 정책이다.

## 미확인 사항

- 실제 provider 또는 외부 네트워크를 사용하는 평가 실행 자체는 수행하지 않았다. 연결 불가 local fixture만 사용했다.

## 7. 다음 작업

- PR 리뷰를 받는다.
- 실제 provider 환경에서 timeout 값이 적절한지 운영 평가 실행 결과와 함께 관찰한다.
