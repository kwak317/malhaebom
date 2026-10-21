# Worklog — Terra 우선 Gemini Fallback 평가 실행

- 일시: 2026-09-23 00:30
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: GitHub README 출력 계약 평가

## 1. 목적

GitHub README 기술스택 평가에서 GPT-5.6 Terra를 기본 모델로 사용하고, 재시도 가능한 호출·출력 계약 실패 시 Gemini 3.8 Flash로 한 번 fallback한다.

## 2. 작업 전 상태

Terra/Gemini fallback 함수는 일부 추가됐지만 기존 다중 모델 비교 loop와 새 loop가 섞여 들여쓰기 오류가 있었고 `MODELS` 참조도 남아 실행할 수 없었다.

## 3. 수행 내용

- `DEFAULT_MODEL`, `FALLBACK_MODEL`, 고정 모델 체인을 정의했다.
- Terra가 408·429·5xx·네트워크·JSON parse·출력 계약 오류일 때만 Gemini를 호출하도록 했다.
- 인증 오류 등 재시도로 해결되지 않는 오류는 fallback하지 않게 했다.
- dry-run과 실제 fallback 실행 요약을 단일 main 흐름으로 정리했다.
- Terra 429 후 Gemini 성공, 401 fallback 금지, dry-run 무네트워크를 단위 테스트했다.

## 주요 판단과 이유

fallback 실행은 두 모델의 독립 품질 비교가 아니라 실제 서비스 장애 대응을 검증하는 경로다. 독립 모델 비교는 별도 평가로 유지해야 한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/run_github_job_fit_comparison.py` | Terra 우선·Gemini fallback 실행 흐름 |
| `evals/test_run_github_job_fit_comparison.py` | fallback 및 dry-run 단위 테스트 |
| `docs/worklogs/2026-09-23_0030_terra-gemini-fallback-test.md` | 작업 기록 |

## 5. 검증

```text
python -m unittest evals.test_run_github_job_fit_comparison
Ran 5 tests in 0.003s
OK

python -m py_compile evals/run_github_job_fit_comparison.py
exit code 0

python evals/run_github_job_fit_comparison.py
{"network_calls": false, "default_model": "openai/gpt-5.6-terra", "fallback_model": "google/gemini-3.8-flash", ...}
```

## 6. 발견한 문제 / 남은 리스크

- 실제 provider 장애 시 fallback 응답 품질과 비용은 아직 재측정하지 않았다.

## 미확인 사항

- 실제 OpenRouter 호출은 비용이 발생하므로 이번 수정 검증에서 수행하지 않았다.

## 7. 다음 작업

- 명시적 사용자 승인 후 `--live --runs 3`으로 실제 fallback 동작을 측정한다.

## 리뷰 후속 수정 (2026-09-23)

- HTTP 403은 권한·접근 거부이므로 재시도 가능한 provider 오류에서 제외했다.
- `HTTP 403` 발생 시 Gemini를 호출하지 않는 회귀 테스트를 추가했다.
- 검증: `./.venv/Scripts/python.exe -m unittest evals.test_run_github_job_fit_comparison` — 6 tests OK.
