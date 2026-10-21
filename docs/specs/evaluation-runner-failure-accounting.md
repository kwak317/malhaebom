# 평가 러너 실패 시간·비용 기록 신뢰성

## Why

- **페르소나**: 동일 평가셋으로 로컬 Ollama와 외부 API 모델을 비교하는 팀원
- **상황**: 30건 평가 중 모델 서버가 응답을 끝내지 않거나, 과금된 응답이 출력 계약을 위반할 수 있다.
- **문제**:
  1. 요청 timeout 이후에도 평가 프로세스가 멈춰 최종 report가 생성되지 않는다.
  2. provider 응답이 완료된 뒤 계약 검증에 실패한 호출의 비용이 누락되면 모델 비교 비용이 실제보다 낮게 집계된다.
- **측정 지표**: timeout 호출의 상한 내 분류율 100%, 완료된 provider 응답의 usage/cost 보존율 100%, timeout 이후 후속 사례 실행 및 report 생성 성공률 100%.

## Goal

- SDK timeout과 별도로 호출을 격리하고 `--timeout-seconds` 안에 끝나지 않은 호출을 강제 종료한다.
- 강제 종료된 호출을 `timeout`으로 기록하고 다음 호출·사례를 계속 실행한다.
- provider 응답을 받은 호출은 Pydantic 또는 서버 validator 실패 여부와 무관하게 token과 비용을 보존한다.
- **Out of Scope**: Ollama 서버 프로세스 종료, 이미 시작된 GPU 계산의 서버 측 취소 보장, 기존 평가 결과 재실행, 모델 품질 또는 기본 모델 변경.

## What

**Happy Path**

1. runner가 모델 호출을 격리 프로세스에서 시작한다.
2. 응답이 제한 시간 안에 도착하면 raw output과 usage를 부모 프로세스로 전달한다.
3. 부모 프로세스가 기존 Pydantic·서버 참조 검증과 채점을 수행한다.
4. report에 실제 token·cost·latency와 검증 결과를 기록한다.

**Edge Cases**

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 호출이 제한 시간을 초과 | 자식 프로세스를 terminate하고 필요 시 kill한 뒤 `timeout` 기록 |
| EC-02 | timeout 호출의 usage를 받지 못함 | 비용을 0이 아닌 `null`, `cost_source=unknown`으로 기록 |
| EC-03 | 응답 JSON 문법 오류 | 응답 전에 확보한 usage·cost를 보존하고 `schema_violation` 기록 |
| EC-04 | Pydantic 출력 계약 위반 | usage·cost를 보존하고 `schema_violation` 기록 |
| EC-05 | 서버 참조 validator 위반 | usage·cost를 보존하고 `validator_violation` 기록 |
| EC-06 | provider가 rate limit 또는 기타 오류 반환 | 민감한 원문 없이 기존 실패 상태로 분류하고 다음 실행 계속 |
| EC-07 | 자식 프로세스가 결과 없이 종료 | `provider_error`로 기록하고 다음 실행 계속 |

## How

- 대상: `evals/run_model_comparison.py`의 실제 OpenAI-compatible/Ollama candidate 호출.
- `--timeout-seconds`는 SDK transport timeout과 부모 프로세스의 hard timeout에 함께 적용한다.
- hard timeout은 각 provider 호출마다 새 프로세스를 사용한다. timeout 후 `terminate` → 짧은 join → 살아 있으면 `kill` 순서로 정리한다.
- 자식은 성공 결과 또는 민감 문자열을 제외한 예외 유형과 이미 확보한 accounting metadata만 반환한다.
- mock candidate는 프로세스 격리를 사용하지 않는다.
- report의 기존 schema와 failure state 이름을 유지한다.

## AC (Given-When-Then)

**AC-01 · 정지 호출 강제 종료**

- GIVEN: provider 호출이 설정 timeout보다 오래 정지한다.
- WHEN: 평가 runner가 해당 호출을 실행한다.
- THEN: 부모는 제한 시간 후 자식을 종료하고 `failure_state=timeout`, `cost_usd=null`로 기록하며 다음 실행을 계속한다.

**AC-02 · 검증 실패 비용 보존**

- GIVEN: provider가 token·cost가 있는 응답을 반환했지만 Pydantic 또는 서버 validator가 거부한다.
- WHEN: runner가 응답을 기록한다.
- THEN: 실패 상태와 함께 provider token·cost가 attempt 및 candidate 합계에 포함된다.

**AC-03 · 정상 호출 회귀 방지**

- GIVEN: provider가 제한 시간 안에 유효한 응답을 반환한다.
- WHEN: runner가 평가한다.
- THEN: 기존 계약 검증·채점·report 필드는 동일하게 생성된다.

**AC-04 · 결과 없는 자식 종료**

- GIVEN: 격리 프로세스가 payload를 보내지 않고 종료한다.
- WHEN: 부모가 종료를 감지한다.
- THEN: 평가 전체를 중단하지 않고 `provider_error` attempt를 기록한다.
