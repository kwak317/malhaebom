# Worklog — GitHub README 출력 계약 강제

- 일시: 2026-09-23 00:15
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: GitHub 기술 증거 기반 공고 핏 진단 제안 Spec

## 1. 목적

README 기반 기술 비교 결과가 README 밖 근거나 채용 적합성 단정 문구를 반환하지 않도록 출력 계약을 서버에서 검증한다.

## 2. 작업 전 상태

스키마에는 `evidence_quote`가 있었지만 formatter는 이전 `evidence` 필드를 읽었다. 금지 표현 목록은 Python 상수가 아니라 프롬프트 문자열 내부에 있었고, 응답 반환 전에 검증 함수가 호출되지 않았다.

## 3. 수행 내용

- 금지 표현 목록을 모듈 상수로 이동했다.
- 프롬프트에 실제 README 연속 인용, 공고 기술 목록 고정, 미확인 인용 null, 질문 형식 규칙을 추가했다.
- 모델 파싱 직후 `validate_result`를 실행하도록 연결했다.
- formatter가 `evidence_quote`를 표시하도록 고쳤다.
- 정확한 원문 인용, README 밖 인용 거부, 채용 적합성 단정 거부를 포함한 단위 테스트를 추가했다.
- 기본 실행은 계획만 출력하고, `--live`를 명시한 경우에만 외부 GitHub/OpenRouter 호출을 수행하도록 유지했다.
- 리뷰 후 `clarifying_question`이 README 기준 미확인 공고 기술 하나만 대상으로 하는지 검증했다.
- 리뷰 후 GitHub 저장소 루트 또는 `blob/main/README.md` URL만 허용하도록 경로 검증을 복구했다.
- 출력 계약 변경 범위 밖인 모델 후보 교체를 되돌리고 기존 비교 모델 목록을 유지했다.

## 주요 판단과 이유

LLM 프롬프트 지시만으로는 README 밖의 프로젝트 구조나 채용 적합성 판단을 막을 수 없다. 서버가 실제 README 원문 포함 여부와 허용된 상태 전이를 검증한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/run_github_job_fit_comparison.py` | 근거·추천·질문·금지 표현 출력 계약 강제 |
| `evals/test_run_github_job_fit_comparison.py` | 출력 계약, 기본 실행 네트워크 차단, 질문 대상, URL allowlist, 모델 목록 단위 테스트 10건 |
| `docs/worklogs/2026-09-23_0015_github-output-contract-enforcement.md` | 작업 기록 |

## 5. 검증

```text
C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe -m unittest evals.test_run_github_job_fit_comparison
Ran 10 tests in 0.003s
OK
```

## 6. 발견한 문제 / 남은 리스크

- 실제 모델은 새 계약에 따라 일부 응답이 거부될 수 있으며, 재시도·수정 prompt 정책은 아직 없다.

## 미확인 사항

- 실제 OpenRouter 재실행은 비용이 발생하므로 수행하지 않았다.

## 7. 다음 작업

- 후보 모델을 동일 README·공고로 재실행해 계약 거부율과 의미 품질을 비교한다.
