# Worklog — 공개 배포 smoke 자동화

- 일시: 2026-10-06 10:15 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: D10 배포 URL, 재현 가능한 검증

## 1. 목적

README의 공개 Frontend·API 주소가 실제로 접근 가능하고 Frontend Origin의 인증 요청을 API CORS가 허용하는지 비밀값 없이 반복 검증하는 단일 명령을 제공한다.

## 2. 작업 전 상태

- 공개 주소는 README에 기록돼 있었고 수동 `curl` 검증 기록도 존재했다.
- 저장소에는 Frontend GET, `/health` JSON, CORS preflight를 함께 검사하는 재실행 도구가 없었다.

## 3. 수행 내용

- 표준 라이브러리만 사용하는 `scripts/check_deployment_smoke.py`를 추가했다.
- Frontend HTTP 200, health HTTP 200과 `status=ok`, CORS의 정확한 Origin·GET·Authorization 허용을 검사한다.
- 로컬 HTTP 서버 기반 성공·비정상 health 테스트를 먼저 작성하고 실패를 확인한 뒤 구현했다.
- 실제 Cloud Run 통합 실행에서 lowercase 응답 헤더 때문에 실패하는 것을 확인했고, lowercase 헤더 회귀 테스트를 추가한 뒤 헤더 이름을 정규화했다.
- README에 기본 실행 명령과 검증 범위 제한을 기록했다.

## 주요 판단과 이유

- 배포 smoke에 새 외부 의존성을 추가하지 않고 Python 표준 라이브러리만 사용한다.
- URL 접근 실패, timeout, 잘못된 health, 불충분한 CORS는 종료 코드 1로 처리한다.
- 인증 토큰이나 사용자 데이터를 전송하지 않으며 공개 네트워크 경계만 확인한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `scripts/check_deployment_smoke.py` | 공개 배포 smoke CLI와 검증 로직 |
| `backend/tests/test_deployment_smoke.py` | 성공·비정상 health·lowercase CORS 회귀 테스트 |
| `README.md` | 재현 명령과 검증 범위 |
| `docs/CURRENT_STATE.md` | 현재 자동화 상태 |
| `docs/worklogs/2026-10-06_1015_deployment-smoke-tool.md` | TDD와 실제 배포 검증 결과 |
| `docs/worklogs/README.md` | Worklog 인덱스 |

## 5. 검증

```text
python backend/tests/test_deployment_smoke.py
Ran 2 tests in 0.577s
OK

python scripts/check_deployment_smoke.py
PASS: frontend: HTTP 200
PASS: health: HTTP 200 {"status":"ok"}
PASS: cors: HTTP 200 origin/method/header allowed

$env:PYTHONPATH = '.;backend;backend/tests'
python -m pytest backend/tests -q
595 passed, 1 failed, 264 subtests passed
실패: test_job_source_e2e_runner.py::test_reads_private_ignored_token_file
원인: Windows에서는 tempfile 파일에 chmod(0o600)를 적용해도 POSIX group/other mode 검사 결과가 유지되어 기존 보안 테스트가 실패함. 이번 변경 파일과 무관함.
```

TDD red 단계에서 구현 모듈 부재를 확인했다. 최초 구현 뒤 실제 배포 통합 실행은 lowercase CORS 헤더 때문에 실패했고, 이를 재현하는 테스트도 수정 전 실패함을 확인했다.

## 6. 발견한 문제 / 남은 리스크

- 공개 endpoint smoke 성공은 인증 후 전체 제품 흐름 성공을 의미하지 않는다.
- 운영 URL이 바뀌면 README와 CLI 기본값을 함께 갱신해야 한다.
- 전체 백엔드 회귀에서 Windows POSIX mode 가정에 의존하는 기존 테스트 1건이 실패했다. 나머지 595건과 264개 subtest는 통과했다.

## 미확인 사항

- 로그인 사용자의 공고 검색·원문 분석·녹음·코칭·재연습 전체 흐름
- 같은 요청의 production Langfuse trace
- Cloud Run 리비전과 Prompt·Skill·model fingerprint

## 7. 다음 작업

- D11 baseline의 오프라인 manifest와 현재 평가 결과 정합성을 별도 브랜치에서 검증한다.
