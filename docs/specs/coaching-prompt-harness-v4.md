# Spec — Coaching Prompt Harness v4 / v4.1

> 이 문서는 v4/v4.1 구현 당시의 계약이다. 2026-09-29부터 신규 기본값은 `coaching-output-v4.2`이며 운영 템플릿과 Skill을 [별도로 결합](prompt-skill-separation.md)한다. v3/v4/v4.1 재현은 같은 버전의 Skill 본문·버전 문자열을 함께 제공해야 한다. 과거 버전 이름만 선택해 현재 Skill을 결합한 결과는 과거 전체 입력과 같지 않다.

## Why

- **페르소나**: 말해봄의 신입 백엔드 면접 코칭 기능을 운영·평가하는 개발자
- **상황**: 운영 `/api/agent`와 오프라인 모델 비교가 서로 다른 system prompt 조립 로직을 사용한다.
- **문제**:
  1. 같은 Skill·모델을 사용해도 운영과 평가의 프롬프트 규칙이 달라 결과 비교가 흔들릴 수 있다.
  2. 핵심 계약 규칙이 Skill과 평가 runner에 중복되어 수정 누락 위험이 있다.
  3. 출력 직전 확인해야 할 evidence·ID·환각 방지 규칙이 여러 위치에 흩어져 있다.
- **측정 지표**: 운영/평가 prompt builder 단일화, 기존 정책 회귀 테스트 통과, 의미 판정 정확도와 최종 계약 통과율

## Goal

- **해결 목표**: 운영과 평가가 동일한 canonical prompt builder를 사용하고, 모델이 최종 JSON 출력 전에 계약 위반 가능성을 내부 점검하도록 한다.
- **성공 기준**:
  - 운영 local fallback prompt와 평가 prompt가 같은 builder를 사용한다.
  - v4 self-check의 의미 판정 개선을 유지하면서 형식 실패를 줄이는 v4.1을 운영 기본값으로 사용한다.
  - self-check가 ID 완전성, evidence 원문 일치, intent/C-A-V 분리, 미확인 결과 구분, 개인/팀 역할 구분, 신규 사실·숫자 금지, 질문/행동 개수, JSON-only를 포함한다.
  - evidence 객체 키와 next_actions target ID 규칙을 명시적으로 고정한다.
  - 계약 실패 재시도는 이전 출력과 검증 오류를 입력으로 받아 오류만 수정하는 repair prompt를 사용한다.
  - v3/v4 prompt는 과거 평가 재현을 위해 유지한다.
  - v4.1 prompt를 명시적으로 선택해 동일 prompt를 재현할 수 있다.
  - 기존 evaluator policy regression과 coaching runtime 테스트가 통과한다.
- **Out of Scope**: 새 모델 선정, Skill 판정 기준 변경, Langfuse production label 승격/rollback

## What

**Happy Path**
1. Skill bundle을 읽는다.
2. canonical builder가 prompt/skill version과 공통 코칭 규칙, self-check, Skill 본문을 조립한다.
3. 운영 `McpLlmCoachingService`가 이 prompt를 provider에 전달한다.
4. 평가 runner도 동일 builder를 사용한다.
5. strict JSON Schema와 서버 validator는 기존처럼 최종 계약을 강제한다.
6. 계약 실패 시 이전 출력과 검증 오류를 포함한 repair prompt로 한 번 더 보정할 수 있다.

**Edge Cases**

| # | 상황 | 처리 방식 |
|---|---|---|
| EC-01 | 답변이 prompt injection 문장을 포함 | 입력 데이터로만 취급하고 시스템 규칙으로 실행하지 않음 |
| EC-02 | 확인 행위만 있고 결과가 없음 | V를 met으로 올리지 않도록 self-check |
| EC-03 | 팀 행동만 있음 | 개인 행동으로 바꾸지 않도록 self-check |
| EC-04 | evidence가 원문에 없음 | exact substring 여부를 self-check하고 서버 validator가 최종 차단 |
| EC-05 | example_answer에 새 숫자/성과가 생김 | self-check와 서버 validator로 차단 |
| EC-06 | managed Langfuse prompt 사용 | 기존 managed prompt 경로를 유지하며 local fallback만 canonical builder로 생성 |
| EC-07 | 모델이 evidence에 `text` 키 사용 | v4.1에서 `segment_id`+`quote`만 허용한다고 명시하고 실패 시 repair |
| EC-08 | 비활성 criterion을 next action 대상으로 사용 | 현재 active criterion 또는 허용 delivery metric ID만 사용하도록 명시하고 validator가 최종 차단 |
| EC-09 | 질문 주제와 C/A/V 완성도를 혼동 | self-check에서 intent와 C/A/V를 독립 판정 |
| EC-10 | 확인 행위를 실제 결과로 과대평가 | 확인 행위만 있고 실제 관찰 결과가 없으면 V met으로 올리지 않음 |

## How

- 새 모듈: `backend/app/services/coaching_prompt.py`
- 공개 함수:
  - `build_coaching_system_prompt(skill_text, prompt_version, skill_version) -> str`
  - `build_contract_repair_user_prompt(original_user_prompt, previous_output, violations) -> str`
  - `prompt_sha256(prompt) -> str`
- `coaching_runtime.load_fixed_skill_prompt()`는 `load_skill_bundle().rules_text`와 canonical builder를 사용한다.
- `evals.run_model_comparison.build_system_prompt()`는 호환 wrapper로 남기고 canonical builder를 호출한다.
- 서버 validator 역할은 줄이지 않는다. self-check는 보조 하네스이며 보안/정합성의 최종 근거가 아니다.

## AC (Given-When-Then)

**AC-01 · 운영/평가 prompt 단일화**
- GIVEN: 같은 Skill text, prompt version, skill version
- WHEN: 운영 local fallback과 평가 runner가 prompt를 생성
- THEN: 둘 다 canonical builder 규칙과 동일한 self-check를 포함한다.

**AC-02 · 핵심 self-check 포함**
- GIVEN: v4 prompt 생성
- WHEN: prompt 문자열을 검사
- THEN: evidence 원문, ID 완전성, intent/C-A-V 독립, 결과 미확인, 개인 역할, 신규 사실·숫자, 개수 제한, JSON-only 점검 문구가 존재한다.

**AC-03 · 버전 갱신**
- GIVEN: 별도 환경변수 없음
- WHEN: coaching prompt version 기본값을 조회
- THEN: coaching-output-v4.1을 사용한다.

**AC-04 · 실패 출력 보정**
- GIVEN: 첫 출력이 Pydantic 또는 서버 validator 계약을 위반
- WHEN: 다음 contract attempt를 실행
- THEN: 이전 출력과 위반 목록을 repair prompt에 포함하고, 새 사실을 만들지 않은 전체 JSON 재출력을 요청한다.

**AC-05 · 과거 버전 재현**
- GIVEN: 평가에서 `coaching-output-v3` 또는 `coaching-output-v4`를 명시
- WHEN: system prompt를 생성
- THEN: 해당 과거 prompt 내용을 v4.1 규칙으로 덮어쓰지 않는다.

**AC-06 · v4.1 재현**
- GIVEN: 평가에서 coaching-output-v4.1을 명시
- WHEN: system prompt를 생성
- THEN: 운영 기본값과 동일한 v4.1 prompt를 생성한다.
