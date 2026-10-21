# 원인 관찰·추론 분리 Spec

## Why

- **페르소나**: 프로젝트 문제 해결 경험을 면접 답변으로 연습하는 신입 백엔드 지원자.
- **상황**: 답변에 “로그에서 원인을 확인했다”는 표현은 있으나, 무엇을 관찰했고 왜 그 관찰로 원인을 좁혔는지 알 수 없다.
- **문제**: 단일 `cause_reasoning` 기준은 관찰 사실과 추론 과정을 한 판정에 섞어 범용 면접 조언과 구별되는 부족 지점을 보여주기 어렵다.
- **측정 지표**: 원인 근거가 불완전한 발표 사례에서 두 기준 중 부족한 요소가 `partial` 또는 `not_observed`로 별도 표시되고, 다음 질문·행동이 그 요소를 정확히 대상으로 한다.

## Goal

- **해결 목표**: `cause_reasoning`을 `cause_observation`과 `cause_inference`로 대체한다.
- **성공 기준**: 같은 답변에 대해 두 기준이 각각 한 번씩 반환되고, 인용문·다음 행동·1차/2차 비교가 새 기준 ID만 참조한다.
- **Out of Scope**: 실제 로그·코드·외부 시스템의 진실성 검증, 기술 원인의 정답 판정, 답변에 없는 관찰·가설·성과 생성, 기존 저장 결과의 자동 의미 변환.

## What

**Happy Path**

1. 서버가 문제 해결 질문에 `cause_observation`, `cause_inference`를 활성 기준으로 제공한다.
2. 모델은 실제 답변 인용만 이용해 두 기준을 독립 판정한다.
3. 서버는 두 ID의 누락·중복·허용되지 않은 action target을 거부한다.
4. 결과 화면과 발표 리포트는 ‘관찰한 신호’와 ‘그 신호로 원인을 좁힌 설명’을 별도 표시한다.
5. 1차/2차 비교는 같은 새 기준 ID끼리만 변화 여부를 계산한다.

**Edge Cases**

| # | 상황 | 처리 방식 |
| --- | --- | --- |
| EC-01 | “로그를 봤다”만 언급 | 관찰 신호가 없으므로 `cause_observation: partial` 또는 `not_observed`; 추론도 별도 판정 |
| EC-02 | 오류·상태 변화는 설명했지만 원인을 연결하지 않음 | `cause_observation: met`, `cause_inference: partial` |
| EC-03 | 원인만 단정하고 관찰 근거가 없음 | `cause_observation: not_observed`, `cause_inference: partial` 또는 `not_observed` |
| EC-04 | 이전 결과가 `cause_reasoning`을 사용 | 새 결과와 직접 비교하지 않으며, 같은 새 Skill 버전으로 재분석해야 비교 가능 |
| EC-05 | 모델이 옛 `cause_reasoning` ID를 반환 | 서버 출력 계약 검증에서 거부하고 1회 repair를 시도 |

## How

- Skill catalog의 허용 ID를 `problem_context`, `cause_observation`, `cause_inference`, `own_action`, `action_rationale`, `result_verification`로 변경한다.
- `cause_observation`: 로그·재현·비교·실험에서 답변이 말한 구체적 신호를 판정한다. 단순히 도구를 사용했다는 표현은 `met` 근거가 아니다.
- `cause_inference`: 관찰한 신호가 특정 원인 후보를 좁히거나 배제하는 판단으로 이어진 설명을 판정한다. 지원자가 원인을 확정하지 못했다고 말하면 그 한계를 유지한다.
- Skill 및 criteria version을 새 값으로 올리고, 질문 문맥·환경 기본값·평가 runner·관측 metadata를 같은 버전으로 맞춘다.
- `CoachingLLMOutput`, 서버 validator, 데모/Supabase 질문 context, 시도 비교 로직, 평가 데이터·tests를 새 ID 계약으로 갱신한다.
- 발표용 비교 runner는 첫 structured output 계약 실패 뒤 동일 모델에 1회 repair를 요청하고, 최종 실패 시 원본 JSON과 오류 필드 경로를 기록한다.

## AC (Given-When-Then)

**AC-01 · 관찰과 추론 분리**
- GIVEN: “서버 로그에서 오류를 확인했다”만 있는 답변
- WHEN: 코칭을 생성한다
- THEN: 모델은 구체적 관찰 신호가 없음을 표시하며 두 기준을 모두 자동 `met`으로 처리하지 않는다.

**AC-02 · 완전한 원인 근거**
- GIVEN: 실제 오류·상태 변화와 그 신호로 원인 후보를 좁힌 연결이 있는 답변
- WHEN: 코칭을 생성한다
- THEN: 두 기준은 각각 `met`이며 각 판정은 실제 답변 인용을 포함한다.

**AC-03 · 구버전 비교 차단**
- GIVEN: 1차 결과가 옛 `cause_reasoning` 기준을 사용한다
- WHEN: 새 기준 결과와 비교하려 한다
- THEN: 서버는 직접 비교를 거부하거나 같은 새 버전으로 재분석하도록 안내한다.

**AC-04 · 계약 강제**
- GIVEN: 모델이 `cause_reasoning`을 반환하거나 새 기준 하나를 누락한다
- WHEN: 서버 validator를 실행한다
- THEN: 결과를 거부하고 repair 후에도 해결되지 않으면 사용자 코칭 응답으로 사용하지 않는다.
