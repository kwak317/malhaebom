# 평가 출력 절단 관측

## Why

- 실제 Gemini 30건 평가에서 `coach-failure-26` 응답이 최대 출력 2,048 토큰 근처에서 잘려 JSON 파싱에 실패했다.
- 격리 자식 프로세스의 `JSONDecodeError`가 상위에서 `provider_error`로 기록되어, 계약 위반과 제공자 장애를 구분할 수 없었다.
- 평가 결과를 보는 팀원은 재실행·출력 한도 조정·모델 비교 판단에 필요한 종료 사유를 확인할 수 있어야 한다.

## Goal

- 격리 실행에서 발생한 JSON 파싱 실패를 `schema_violation`으로 기록한다.
- OpenAI-compatible 응답의 `finish_reason`을 attempt 원본 기록에 보존한다.
- `finish_reason=length`인 잘린 응답을 결과에서 판별할 수 있게 한다.

Out of Scope: 운영 API의 재시도 정책 변경, 모델 Prompt 변경, 평가셋·정답 변경, 결과 원본의 Git 커밋.

## What

**Happy Path**

1. 평가 runner가 provider 응답의 첫 choice `finish_reason`을 기록한다.
2. 정상 JSON은 기존 validator·점수 집계를 유지한다.

**Edge Cases**

- 격리 자식에서 `JSONDecodeError` 발생: `schema_violation`으로 분류하고 민감한 SDK 메시지는 저장하지 않는다.
- 격리 자식에서 timeout 발생: 기존 `timeout` 분류를 유지한다.
- choice 또는 finish reason 누락: 필드를 기록하지 않으며 기존 동작을 유지한다.

## How

- 대상: `evals/run_model_comparison.py`의 `OpenAICompatibleRunner._generate_direct` 및 `_provider_failure_state`.
- `last_record`에 `finish_reason`을 추가한다.
- `IsolatedProviderError.error_type`이 `JSONDecodeError` 또는 `ValueError`면 `schema_violation`을 반환한다.
- 기존 `backend/tests/test_evaluation_records.py`에서 strict schema 요청·격리 실패 회귀를 확장한다.

## AC

- GIVEN 격리 자식이 `JSONDecodeError`를 반환할 때 WHEN 평가가 failure state를 결정하면 THEN 결과는 `schema_violation`이다.
- GIVEN provider choice의 `finish_reason`이 `length`일 때 WHEN attempt를 직렬화하면 THEN 원본 attempt에 `finish_reason: length`가 있다.
- GIVEN 다른 provider 오류일 때 WHEN 분류하면 THEN 기존 `provider_error` 분류를 유지한다.
