# 범용 AI와 말해봄 비교 증거 Spec

## Why

- **페르소나**: 발표에서 동일 모델을 사용했을 때 말해봄의 프로젝트 설계가 만든 차이를 설명하는 팀원.
- **상황**: 범용 Gemini 웹 UI와 말해봄은 숨겨진 시스템 지침과 실행 환경이 달라, 직접 비교만으로는 차이의 원인을 입증하기 어렵다.
- **문제**: 모델 자체의 성능 차이와 말해봄의 Skill·문맥·검증 설계 차이를 구분해 재현 가능한 증거로 제시할 방법이 없다.
- **측정 지표**: 한 PowerShell 명령으로 합성 사례별 Markdown/JSON 비교 리포트가 생성되고, 각 사례에서 두 조건의 입력 범위와 말해봄 계약 검증 상태를 확인할 수 있다.

## Goal

- **해결 목표**: 같은 모델 ID·질문·답변·최대 출력 토큰으로 범용 피드백과 말해봄 코칭을 실행·기록한다.
- **성공 기준**: API 키 없이 mock 리포트를 생성하고, live 실행 시 범용 출력과 말해봄 구조화 출력을 같은 사례에 함께 저장한다.
- **Out of Scope**: Gemini 웹 UI 자동화, 실제 사용자 전사문 전송, 범용 응답의 정답 점수화, 모델 선정 지표 변경, 운영 API/UI 변경.

## What

**Happy Path**

1. 합성 평가셋에서 지정 사례를 선택한다.
2. 범용 조건에는 질문·답변만 주고 자유 형식 피드백을 받는다.
3. 말해봄 조건에는 canonical Skill·서버 문맥·구조화 출력 계약을 주고 검증한다.
4. 사례별 두 출력과 말해봄 계약 결과를 JSON 및 Markdown으로 저장한다.

**Edge Cases**

| # | 상황 | 처리 방식 |
| --- | --- | --- |
| EC-01 | API 키 없이 실행 | 기본 `mock` 모드로 외부 호출 없이 리포트 형식 생성 |
| EC-02 | 범용 호출 실패 | 해당 사례에 실패 유형을 기록하고 말해봄 조건은 계속 실행 |
| EC-03 | 말해봄 JSON/서버 계약 실패 | 계약 검증 실패를 기록하고 유효한 결과로 표시하지 않음 |
| EC-04 | 존재하지 않는 case ID | 외부 호출 전 오류로 종료 |
| EC-05 | 실제 사용자 자료 사용 | 지원하지 않음; 합성 `dataset.v2.jsonl`만 기본 입력으로 사용 |

## How

- 실행기: `evals/generic_vs_malhaebom.py`
- 기본 모델: `google/gemini-3.5-flash-lite`; `--model`로 명시 가능
- 범용 입력: `question`, `answer` 두 필드만 포함한다.
- 말해봄 입력: 기존 canonical prompt v4.1, `skills/interview-coach/SKILL.md`, 평가 사례의 구조화 server context, strict JSON schema 및 서버 validator를 사용한다.
- 원인 근거 발표 사례는 `cause_observation`, `cause_inference`를 각각 활성화하며, 구체적 관찰 신호와 그 신호로 원인 후보를 좁힌 연결이 부족하면 각 기준을 독립적으로 `partial`로 기대한다.
- live 호출은 `MODEL_API_KEY`, `MODEL_API_BASE_URL`이 있을 때 `--mode live`로만 수행한다.
- structured output이 provider에서 JSON 문자열로 한 번 더 감싸져도 한 겹만 해제한다. 발표 사례의 다섯 기준 JSON이 잘리지 않도록 기본 최대 출력은 2,048 토큰이며, 두 조건에 같은 값을 사용한다.
- 결과는 기본적으로 Git 제외 대상인 `local-results/generic-vs-malhaebom/`에 `comparison.json`, `comparison.md`로 저장한다.

## AC (Given-When-Then)

**AC-01 · 범용 입력 경계**
- GIVEN: 합성 평가 사례 하나
- WHEN: 범용 입력을 구성한다
- THEN: 질문과 답변만 포함하고 공고·기준·서버 문맥은 포함하지 않는다.

**AC-02 · 비교 리포트**
- GIVEN: 범용 및 말해봄 결과가 있는 사례
- WHEN: Markdown을 생성한다
- THEN: 입력, 범용 AI 출력, 말해봄 출력, 말해봄 계약 검증 상태가 함께 표시된다.

**AC-03 · 범용 결과 과대해석 방지**
- GIVEN: 비교 Markdown
- WHEN: 독자가 결과를 확인한다
- THEN: 범용 AI 응답은 정확도 점수로 환산하지 않는다는 제한을 확인할 수 있다.
