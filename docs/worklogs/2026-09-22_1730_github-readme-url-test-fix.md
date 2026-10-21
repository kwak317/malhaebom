# Worklog — GitHub README URL 테스트 경로 수정

- 일시: 2026-09-22 17:30
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: GitHub 기술 증거 기반 공고 핏 진단 제안 Spec

## 1. 목적

`evals/run_github_job_fit_comparison.py`가 사용자가 제공한 GitHub README URL을 받아 README API 주소로 바꾸게 한다.

## 2. 작업 전 상태

사용자가 저장소 루트 대신 `.../blob/main/README.md` URL을 설정해 실행했고, URL 경로 길이만 검사하던 함수가 `ValueError`로 중단됐다.

## 3. 수행 내용

- README blob URL을 입력한 단위 테스트를 추가하고 실패를 확인했다.
- 저장소 루트 URL과 `main` 브랜치 README blob URL을 모두 허용하도록 URL 변환을 수정했다.
- 저장소 루트 URL 회귀 테스트를 추가했다.

## 주요 판단과 이유

공개 GitHub README만 분석하는 현재 테스트 범위를 유지하기 위해 임의 경로는 허용하지 않고 저장소 루트 또는 `main`의 README URL만 허용했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/run_github_job_fit_comparison.py` | README blob URL 정규화 지원 |
| `evals/test_run_github_job_fit_comparison.py` | URL 변환 단위 테스트 2건 |
| `docs/worklogs/2026-09-22_1730_github-readme-url-test-fix.md` | 작업 기록 |

## 5. 검증

```text
C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe -m unittest evals.test_run_github_job_fit_comparison
Ran 2 tests in 0.000s
OK
```

## 6. 발견한 문제 / 남은 리스크

- 실제 모델 호출에는 `OPENROUTER_API_KEY`가 필요하며 비용이 발생하므로 실행하지 않았다.

## 미확인 사항

- OpenRouter의 두 후보 모델 실제 응답 품질·비용·지연은 측정하지 않았다.

## 7. 다음 작업

- 사용자 승인 후 API 키가 설정된 환경에서 두 후보 모델을 동일 입력으로 실행하고 결과를 비교한다.
