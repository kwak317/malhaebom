# Worklog — GitHub 공고 핏 모델 비교 출력 개선

- 일시: 2026-09-22 17:45
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: GitHub 기술 증거 기반 공고 핏 진단 제안 Spec

## 1. 목적

모델 비교 결과를 사람이 읽을 수 있는 기술 표와 보완 추천 목록으로 표시하고, 모델별 기본 3회 반복 실행의 비용·지연·성공 수를 요약한다.

## 2. 작업 전 상태

기존 runner는 모델당 한 번의 JSON 원문만 출력했다. 사용자는 기술별 비교와 보완 우선순위를 빠르게 파악하기 어려웠다.

## 3. 수행 내용

- 구조화 출력에 `recommended_skills`(최대 2개)를 추가했다.
- 추천은 공고에 있으나 README에서 확인되지 않은 기술만 대상으로 하고, 이유와 다음 행동을 반환하도록 prompt를 제한했다. 모델 응답은 확인 기술의 형식, 공고 기술스택 전체, 중복 없는 기술명, 허용 상태, 추천 상한, 추천 대상의 README 미확인 상태를 검증한 뒤에만 성공 통계에 반영한다.
- 기술별 표, 확인/미확인 요약, 보완 추천, 추가 질문, 실행별 지연·비용을 출력하도록 formatter를 추가했다.
- 모델당 기본 3회 반복과 모델 간 성공 수·평균 응답 시간·총 비용 요약을 추가했다.
- 기본 실행은 호출 계획만 출력하고, 공개 README 전송과 OpenRouter 유료 호출은 `--live`를 명시한 경우에만 수행하도록 했다.

## 주요 판단과 이유

README 기준 미확인은 사용자의 경험 부재를 뜻하지 않는다. 따라서 추천 문구는 학습 또는 README 근거 보완을 제안하되 경험 없음·부족으로 단정하지 않게 했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/run_github_job_fit_comparison.py` | 3회 비교, 가독성 출력, 보완 추천 기술 계약 |
| `evals/test_run_github_job_fit_comparison.py` | 가독성 출력 단위 테스트 |
| `docs/worklogs/2026-09-22_1745_github-job-fit-readable-output.md` | 작업 기록 |

## 5. 검증

```text
C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe -m unittest evals.test_run_github_job_fit_comparison
Ran 9 tests in 0.002s
OK

C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe -m py_compile evals\run_github_job_fit_comparison.py
exit code 0

C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe evals\run_github_job_fit_comparison.py
{"network_calls": false, "planned_models": ["google/gemini-3.1-flash-lite", "google/gemini-3.8-flash"], "planned_runs_per_model": 3, "planned_model_calls": 6}

python -m unittest discover -s backend/tests
Ran 76 tests, FAILED (errors=38): 현재 Python 환경에 fastapi, pydantic, httpx, PyJWT, numpy 등이 없어 import 단계에서 실패했다. 이 runner 변경과 직접 관련된 실패는 확인하지 못했다.
```

## 6. 발견한 문제 / 남은 리스크

- 모델이 README 밖 근거를 인용하는지와 추천 품질은 실제 3회 실행 결과를 사람이 별도 점검해야 한다.
- 전체 backend 회귀 테스트는 프로젝트 의존성이 준비된 환경에서 다시 실행해야 한다.

## 미확인 사항

- 실제 OpenRouter 호출과 모델별 비용·지연·안정성 측정은 수행하지 않았다.

## 7. 다음 작업

- API 키가 설정된 환경에서 `--live`로 3회 실행 후 README 원문과 결과 근거를 대조한다.
