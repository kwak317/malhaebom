# Worklog — 평가 러너 timeout·비용 기록 신뢰성

- 일시: 2026-09-22 14:18 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: GitHub Issues #22, #32
- 관련 요구사항/결정: `docs/specs/evaluation-runner-failure-accounting.md`, `evals/README.md`

## 1. 목적

OpenAI-compatible/Ollama 평가 호출이 SDK timeout을 넘어 정지해도 평가 전체가 진행되게 하고, provider 응답 후 출력 계약 검증에 실패한 호출의 token·cost가 누락되지 않게 한다.

## 2. 작업 전 상태

- `evals/run_model_comparison.py`는 OpenAI SDK에 timeout과 `max_retries=0`을 전달했지만 호출 자체는 현재 평가 프로세스 안에서 실행했다.
- Issue #32 기록상 Qwen3/EEVE 30건 실행이 timeout 이후에도 종료되지 않아 report를 만들지 못했다.
- Issue #22 본문과 달리 최신 main은 provider 응답의 `last_record.usage`를 검증 예외 뒤에도 복원했고, `test_validator_failure_retains_usage_and_id_metric`가 validator 실패 비용 보존을 이미 검사했다. 이 동작을 회귀 범위에 포함했다.
- 작업 전 Git 상태는 깨끗했다. 최신 `main`을 fast-forward한 뒤 `fix/evaluation-runner-reliability` 브랜치를 생성했다.

## 3. 수행 내용

- Why·Goal·What·How·AC를 갖춘 평가 러너 실패 처리 Spec을 작성했다.
- 실제 provider 호출마다 spawn 자식 프로세스를 만들고 부모가 `--timeout-seconds` 동안만 결과를 기다리게 했다.
- hard timeout 시 자식을 terminate하고, 종료되지 않으면 kill한 뒤 `timeout`으로 분류하게 했다.
- 자식은 원문 오류 대신 예외 유형과 이미 확보한 usage/raw output metadata만 부모에 전달하게 했다.
- timeout으로 usage를 받지 못한 경우 비용을 `null`/unknown으로 유지하고, 응답 후 JSON·Pydantic·validator 실패는 기존 token·cost를 보존하게 했다.
- timeout 값의 양수 검증, 운영 문서와 현재 상태 문서를 갱신했다.

## 주요 판단과 이유

- thread timeout은 정지한 요청 thread를 종료할 수 없고 Python 종료까지 막을 수 있어 프로세스 격리를 사용했다.
- Ollama 서버 프로세스 자체를 종료하지 않는다. 평가 runner의 클라이언트 호출 종료와 서버 내부 GPU 계산 취소는 별개이기 때문이다.
- 강제 종료된 호출의 비용은 provider 응답을 받지 못했으므로 0으로 단정하지 않고 unknown으로 기록한다.
- mock runner는 외부 정지 가능성이 없고 빠른 회귀 검증에 사용되므로 격리하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/specs/evaluation-runner-failure-accounting.md` | 실패 timeout·비용 기록 계약과 AC 추가 |
| `evals/run_model_comparison.py` | provider 호출 프로세스 격리, hard timeout, 안전한 오류 전달 추가 |
| `backend/tests/test_evaluation_records.py` | hard timeout 종료, 격리 오류, 비용 보존 회귀 테스트 추가 |
| `evals/README.md` | timeout과 비용 unknown 동작 및 한계 문서화 |
| `docs/CURRENT_STATE.md` | 현재 구현 상태와 실제 Ollama 미재실행 상태 반영 |
| `docs/worklogs/2026-09-22_1418_evaluation-runner-reliability.md` | 수행·검증·미확인 사항 기록 |

## 5. 검증

```text
env PYTHONPATH=backend/tests .venv-llm-eval/bin/python -m unittest \
  backend.tests.test_evaluation_records \
  backend.tests.test_coaching_eval_v2 \
  backend.tests.test_evaluator_policy_alignment -v
결과: 24 tests, OK
```

```text
.venv-llm-eval/bin/python -B evals/run_model_comparison.py \
  --candidate expected=mock:expected \
  --candidate degraded=mock:degraded \
  --output-dir /tmp/malhaebom-eval-runner-reliability
결과: comparison.json/comparison.md 생성, 60 attempts, expected contract_rate=1.0
```

```text
.venv-llm-eval/bin/python -m py_compile \
  evals/run_model_comparison.py backend/tests/test_evaluation_records.py
결과: 통과
```

```text
git diff --check
결과: 통과
```

## 6. 발견한 문제 / 남은 리스크

- 전체 backend unittest discovery는 90초 이상 출력 없이 대기하여 중단했다. 관련 24개 테스트는 별도로 모두 통과했다.
- hard timeout은 클라이언트 자식 프로세스를 종료하지만 Ollama 서버가 이미 시작한 GPU 계산의 즉시 취소를 보장하지 않는다.

## 미확인 사항

- 실제 Qwen3/EEVE 30건 전체 실행과 최종 report 생성은 GPU/Ollama 환경에서 재실행하지 않았다.
- Windows에서의 실제 Ollama spawn 실행은 이번 환경에서 확인하지 않았다.

## 7. 다음 작업

- 사용 가능한 Ollama/GPU 환경에서 한 건 preflight 후 Qwen3/EEVE 30건을 동일 설정으로 재실행한다.
- 재현 결과를 Issue #32에 연결하고, #22는 현재 비용 보존 테스트 근거와 함께 종료 여부를 검토한다.
