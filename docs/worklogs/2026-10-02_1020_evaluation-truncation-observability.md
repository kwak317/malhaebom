# Worklog — 평가 출력 절단 관측

- 일시: 2026-10-02 10:20 KST
- 작업자/에이전트: Codex
- 관련 PR: 후속 PR 예정
- 관련 요구사항/결정: D3 실제 모델 출력 계약, D4 재현 가능한 평가 기록

## 1. 목적

실제 Gemini 평가에서 잘린 JSON이 일반 제공자 오류로 기록되는 문제를 고쳐, 계약 위반과 제공자 장애를 구분한다.

## 2. 작업 전 상태

`local-results/gemini-v5-live-30/comparison.json`에서 `coach-failure-26`이 2,032 completion tokens와 불완전한 JSON 원문을 남겼지만 `provider_error`로 기록됐다. 격리 자식의 `JSONDecodeError`가 `IsolatedProviderError`로 감싸진 뒤 분류 함수가 그 error type을 해석하지 못한 것이 원인이었다.

## 3. 수행 내용

- provider의 첫 choice `finish_reason`을 attempt 원본 기록에 추가했다.
- 격리된 `JSONDecodeError`와 `ValueError`를 `schema_violation`으로 분류했다.
- 출력 절단의 실제 수치·한계를 실험 문서에 기록했다.
- 회귀 테스트로 종료 사유 보존과 오류 분류를 확인했다.

## 주요 판단과 이유

모델·Prompt·재시도 정책은 바꾸지 않았다. 이번 변경은 관측·분류만 다루며, 출력 한도 4,096의 실제 재평가는 별도 유료 호출로 분리한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/run_model_comparison.py` | finish reason 기록과 격리 JSON 오류 분류 복구 |
| `backend/tests/test_evaluation_records.py` | 두 회귀 테스트 추가 |
| `docs/specs/evaluation-truncation-observability.md` | 변경 범위와 AC |
| `docs/experiments/2026-10-02_gemini-v5-30case-evaluation.md` | 실제 평가 결과와 한계 |
| 본 파일 | 작업 기록 |

## 5. 검증

```text
targeted evaluation-record tests: 2 passed
python -m unittest discover -s backend/tests -p 'test_coaching*.py': 110 passed
python -m unittest backend.tests.test_evaluation_records: 8 passed
git diff --check: passed
```

## 6. 발견한 문제 / 남은 리스크

- `max_completion_tokens=2048`은 긴 failure case에서 JSON 절단을 일으킬 수 있다.
- 유효 응답 중 의미 판정 불일치는 사람 검토가 필요하다.

## 미확인 사항

- 4,096 token 상한의 실제 Gemini 30건 결과는 아직 없다.

## 7. 다음 작업

- 후속 PR 리뷰 후 4,096 token 상한으로 별도 결과 폴더에 실제 30건 재실행한다.
