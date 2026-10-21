# 코칭 출력 계약과 서버 검증 Spec

## Why

- **페르소나**: 지원 공고에 맞춰 문제 해결 경험을 연습하는 신입 개발자 취업준비생
- **상황**: 확인된 답변을 LLM이 분석해 공고 관련성, 질문 의도, 기준별 판정과 다음 행동을 반환한다.
- **문제**:
  1. 형식만 맞는 JSON도 허용되지 않은 기준 ID나 문장 ID를 만들 수 있다.
  2. 답변에 없는 문장을 근거처럼 인용하면 사용자가 잘못된 코칭을 받는다.
  3. LLM이 `status`, 통합 `evidence`, `gaps`까지 만들면 기준별 판정과 최종 응답이 서로 달라질 수 있다.
- **측정 지표**: 고정 입력에서 형식·참조 위반을 모두 차단하고, 정상 입력의 사용자 응답 필드가 계약과 일치한다.

## Goal

- Pydantic으로 내부 LLM 출력의 필수 필드, 허용 상태, 배열 길이와 상태별 일관성을 검증한다.
- 서버가 보유한 요구사항 ID, 활성 기준 ID, 답변 문장 ID와 행동 대상만 허용한다.
- 모든 인용문이 지정한 현재 답변 문장에 정확한 부분 문자열로 존재하는지 확인한다.
- 검증된 기준별 결과로 `status`, 통합 `evidence`, `gaps`를 서버에서 계산한다.
- `unsupported`, `unavailable` 응답은 LLM 결과를 사용하지 않고 서버에서 생성한다.

**성공 기준**: 정상·정보 부족·범위 밖·검증 실패를 포함한 AC 테스트가 모두 통과하고, 최종 응답이 합의한 8개 핵심 필드만 반환한다.

**Out of Scope**: 실제 LLM API 호출, 재시도·폴백, `/api/agent` 공개 엔드포인트, MCP·Langfuse 연결, DB 저장, 인용 해석의 의미상 적절성 평가.

## What

**Happy Path**

1. 서버가 선택 요구사항 ID, 활성 기준 ID와 확인된 답변 문장을 `ServerValidationContext`로 구성한다.
2. LLM의 JSON을 `CoachingLLMOutput`으로 형식 검증한다.
3. 서버 검증 함수가 ID의 중복·누락, 문장 참조, 인용문, 행동 대상을 확인한다.
4. 검증에 통과하면 `status`, 통합 `evidence`, `gaps`를 계산해 `CoachingResponse`를 반환한다.

**Edge Cases**

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 필수 필드 누락, 알 수 없는 필드, 허용되지 않은 상태 | Pydantic 검증 실패로 결과 전체를 거부한다. |
| EC-02 | 요구사항·활성 기준 ID의 중복, 누락 또는 임의 ID | 서버 컨텍스트와 정확히 대조해 거부한다. |
| EC-03 | 존재하지 않는 문장 ID 또는 문장에 없는 인용문 | 사용자 응답을 만들지 않고 거부한다. |
| EC-04 | `met`·`partial`의 근거 누락 또는 `needed` 모순 | 상태별 계약 위반으로 거부한다. |
| EC-05 | 행동이 비활성 기준이나 허용되지 않은 전달력 지표를 참조 | 행동 대상 검증 실패로 거부한다. |
| EC-06 | 지원 범위 밖 요청 또는 시스템 실패 | 빈 판정 목록과 `undetermined` 의도로 서버 응답을 만든다. |

## How

- Pydantic 모델: `backend/app/schemas/coaching.py`
- 서버 참조 검증과 계산: `backend/services/llm.py`
- 테스트: `backend/tests/test_coaching_validation.py`
- LLM 내부 출력은 `job_alignment`, `intent_assessment`, `criterion_assessments`, `clarifying_question`, `next_actions`만 생성한다.
- 사용자 응답은 `status`, `job_alignment`, `intent_assessment`, `criterion_assessments`, `evidence`, `gaps`, `clarifying_question`, `next_actions`의 8개 핵심 필드로 구성한다.
- 인용 검증은 공백 정규화나 유사도 비교 없이 현재 답변 문장의 정확한 부분 문자열만 인정한다.
- 의미상 인용 적절성은 문자열 검사로 보장하지 않고 평가셋과 사람 검토로 별도 측정한다.

## AC (Given-When-Then)

- **AC-01 · 정상 정보 부족 응답**
  - GIVEN: 허용된 ID와 실제 답변 인용이 있고 일부 기준이 `not_observed`다.
  - WHEN: 서버 검증 함수를 실행한다.
  - THEN: `needs_more_info`, 계산된 `gaps`, 연결된 통합 `evidence`를 반환한다.
- **AC-02 · 완전 충족 응답**
  - GIVEN: 모든 공고 관련성이 `related`, 질문 의도가 `aligned`, 모든 기준이 `met`다.
  - WHEN: 서버 검증 함수를 실행한다.
  - THEN: `ok`, 빈 `gaps`, `null` 확인 질문을 반환한다.
- **AC-03 · 잘못된 인용 차단**
  - GIVEN: 인용문이 지정한 답변 문장에 존재하지 않는다.
  - WHEN: 서버 검증 함수를 실행한다.
  - THEN: 결과 전체를 `OutputContractError`로 거부한다.
- **AC-04 · 기준 ID 중복·누락 차단**
  - GIVEN: 활성 기준이 누락되고 다른 기준이 중복됐다.
  - WHEN: 서버 검증 함수를 실행한다.
  - THEN: 중복과 누락을 모두 오류로 반환한다.
- **AC-05 · 행동 대상 차단**
  - GIVEN: 행동이 활성화되지 않은 기준을 참조한다.
  - WHEN: 서버 검증 함수를 실행한다.
  - THEN: 허용되지 않은 행동 대상으로 거부한다.
- **AC-06 · 범위 밖·실패 응답**
  - GIVEN: 서버가 `unsupported` 또는 `unavailable`을 결정했다.
  - WHEN: terminal 응답을 만든다.
  - THEN: 판정·근거·부족 항목·행동은 빈 배열이고 의도는 `undetermined`다.
