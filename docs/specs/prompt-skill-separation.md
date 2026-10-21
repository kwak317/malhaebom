# 프롬프트와 도메인 Skill 분리

## Why

모델 역할·출력 형식과 면접/원문 판단 규칙이 Skill 및 Python system prompt에 중복돼 있다. 특히 README·공고 분석은 Skill의 version만 읽고 본문 규칙은 Python에 다시 적어 실제 Skill 수정이 모델 입력에 반영되지 않는다.

## Goal

- 코칭·README 분석·공고 요구사항 분석·면접 대화의 모델 운영 지침을 `prompts/`, 도메인 판단을 `skills/`에서 독립적으로 관리한다.
- 요청 구성 시 프롬프트 템플릿과 선택된 Skill 규칙을 합성한다. 외부 원문은 user prompt 데이터로만 전달한다.
- 기존 API·스키마·서버 검증·재시도·MCP·로컬 대화 보관 기능을 유지하고, 과거 코칭 v3/v4/v4.1 빌더는 재현용으로 보존한다.
- 검색 공급자·새 Skill·RAG·도구 선택 방식·Langfuse Cloud 게시·배포는 이번 변경에 포함하지 않는다.

## What

- Prompt: 모델 역할, 원문 안의 지시를 데이터로 취급하는 규칙, 한국어 응답, JSON 필드·응답 방식, 출력 전 계약 점검.
- Skill: 질문별 판정 기준, 원문 인용·허용된 근거, 팀/개인 행동 구분, 관찰/추론/검증 구분, 공고 우대/필수의 해석, 대화 질문·요약의 도메인 규칙.
- Skill에도 근거 입력의 신뢰 경계를 유지해 이전 v3 빌더 경로를 보호한다. 모든 활성 기준 충족 시 질문을 만들지 않는 판단은 Skill에, 질문 없는 결과의 `null` 표기는 Prompt에 둔다.
- Skill 본문이나 Prompt 파일 누락/공백은 명시적으로 실패한다.
- Langfuse 후보 동기화는 Skill 본문을 포함하지 않는 템플릿을 관리한다. 런타임은 `{{skill_text}}` 위치에 현재 Skill을 결합한다. 이 슬롯이 없는 과거 원격 완성 프롬프트는 로컬 프롬프트로 fallback한다.

### Canonical rule ownership

코칭의 **단일 기준원은 한 파일이 아니라 `load_skill_bundle()`이 조립하는 versioned Skill bundle 하나**다.
새 운영 Prompt나 새 후보 Prompt는 아래 소유권을 뒤집어 자체 판정표·수치 기준을 다시 정의하지 않는다.

| 구성 | canonical 소유 범위 |
| --- | --- |
| `skills/interview-coach/criteria.json` | criterion ID·이름·버전·검토 상태와 기계 판독 가능한 met/partial/not_observed/undetermined 계약 |
| 질문 유형 문서(`problem-solving.md`, `preset-interview.md`) | 유형별 의미, 경계 판정, 우선순위와 도메인 예시 |
| `skills/interview-coach/SKILL.md` | 공통 판정 절차, 입력 신뢰 경계, 증거·사실 보존 규칙 |
| `prompts/*.md`의 현재 운영 템플릿 | 역할, 입력/실행 경계, JSON 출력 계약, 내부 계약 점검 |

- 제품 판정용 **고정 숫자 임계값은 현재 Skill bundle에 두지 않는다.** 예를 들어 `700ms` 같은 값은 평가 입력의 사례값일 수는 있지만 “700ms 이하면 met” 같은 제품 기준으로 승격하지 않는다.
- `coaching-output-v3/v4/v4.1`, 배포 archive, 과거 실험 Prompt처럼 재현을 위해 동결한 자산은 판정 규칙을 중복 포함할 수 있다. 이들은 **재현 snapshot**이며 새 판정 기준의 출처가 아니다. hash 재현성을 위해 중복 문구를 정리한다는 이유로 수정하지 않는다.
- 신규 후보는 가능한 한 `coaching-v5-skill-owned`처럼 도메인 판정표를 Skill bundle에만 두는 구조를 사용한다.
- 평가셋의 숫자·문장과 expected label은 회귀 테스트 데이터이며 제품의 canonical rule source가 아니다.

## How

- `prompts/coaching.md`, `github-readme-analysis.md`, `job-requirement-analysis.md`, `interview-conversation.md`를 기본 프롬프트로 사용한다.
- `SkillBundle.rules_text`는 도메인 규칙 묶음이고 최종 system prompt가 아니다. `criteria.json`의 루브릭·버전·서버 검증은 그대로 유지한다.
- README·공고 분석은 검증된 Skill 본문을 직접 조합한다. 면접 대화는 기존 Skill 문서와 별도 출력 프롬프트를 조합한다.
- 신규 코칭 기본 프롬프트는 `coaching-output-v4.2`. v3/v4/v4.1 빌더는 동일 Skill 문자열·버전 입력에서 이전 조합을 보존한다. 현재 Skill을 넣은 결과가 과거 전체 Prompt와 같다는 뜻은 아니며, 완전 재현에는 당시 Skill snapshot도 필요하다.
- 두 Dockerfile에 `prompts/`를 포함한다. 현재 `.env`, DB, 실행 컨테이너는 변경하지 않는다.

## AC

1. Given 다른 규칙의 Skill 두 개 When 같은 템플릿으로 요청 Then 각 본문과 버전이 반영되고 역할·출력 지침은 공통으로 유지된다.
2. Given 수정한 README/공고 Skill When 분석 Then Python에 하드코딩한 대체 규칙이 아니라 해당 Skill 본문이 provider 입력에 들어간다.
3. Given Langfuse 템플릿 When 로딩 Then 현재 Skill을 결합한다. Given 슬롯 없는 원격 완성 Prompt Then 로컬 Prompt와 현재 Skill을 사용한다.
4. Given v3/v4/v4.1과 동일 Skill 문자열 When 생성 Then 이전 빌더의 hash가 유지된다.
5. Given 정상/허위 인용/중복/불허 ID/보정/저장 실패 When 기존 회귀 테스트 Then 기존 API 상태와 검증 동작이 유지된다.
