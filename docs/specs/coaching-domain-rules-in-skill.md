# 코칭 도메인 규칙의 Skill 관리

## Why
영문 v4 Prompt와 Skill이 같은 도메인 규칙을 중복 정의하며 결과 검증의 인정 조건이 다르다.

## Goal
명시적으로 선택하는 v5 템플릿의 도메인 판정 규칙·판정 예시를 Skill에서 관리한다. 기존 v4 템플릿과 실험 결과는 보존한다. 배포, Langfuse 변경, 실제 LLM 재평가는 제외한다.

## What
- 새 영문 v5 템플릿은 Skill 적용 지시, 입력 경계, 출력 계약만 제공한다.
- 판정 의미와 긍정·부정 예시는 Skill 본문에 둔다.
- 상충하는 결과 검증 예시는 기존 Skill의 ‘방법·조건과 실제 관찰 결과’ 기준으로 통일한다. 실제 수치가 없다는 이유만으로 부족 판정하지 않는다.

## How
- 2026-10-06 사용자 요청으로 기본 Prompt는 배포 기준 `coaching-user-supplied-v4-verification`이다. v5는 `COACHING_PROMPT_VERSION=coaching-v5-skill-owned`로 명시 선택하며 기존 버전 선택은 유지한다.
- Skill 버전을 `interview-coach-v6.1-domain-rules`로 갱신한다. 질문과 연결된 criteria_version 및 판정 enum은 유지한다.
- 서버의 JSON Schema, ID·인용 검증, 보정 루프는 변경하지 않는다.
- Langfuse에 기존 템플릿이 설정되어 있으면 별도 갱신이 필요하며 이번 작업에서는 외부 설정을 변경하지 않는다.

## AC
- Given v5 명시 설정, When 운영 및 평가 builder를 호출, Then 동일한 v5 템플릿과 현재 Skill을 결합한다.
- Given Skill 없는 v5 템플릿, Then 개인 행동·결과 검증 판정 규칙과 도메인 예시가 존재하지 않는다.
- Given Skill 교체, When 동일 템플릿을 결합, Then 교체된 Skill만 도메인 규칙으로 포함된다.
- Given 이전 v4 선택, Then 기존 템플릿을 그대로 로드한다.
- 관련 Prompt·Skill·runtime·검증 테스트가 통과한다. 테스트 결과를 실제 LLM 품질 점수로 표현하지 않는다.
