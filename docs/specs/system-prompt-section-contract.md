# System Prompt 섹션 계약

## Why

프롬프트 설계 점검에서는 각 LLM 호출의 system Prompt가 **역할·입력 경계·출력 계약·안전 경계**를 명시적으로 분리해야 한다. 기존 구현은 필요한 규칙 자체는 대부분 갖고 있었지만 Markdown Prompt와 Python inline Prompt의 구조가 서로 달랐다.

## 표준 섹션

새로 작성하거나 수정하는 mutable system Prompt는 아래 순서를 사용한다.

1. `[역할]`
2. `[입력 경계]`
3. `[출력 계약]`
4. `[안전 경계]`

Skill을 합성하는 호출은 뒤에 `[고정 Skill]`을 추가할 수 있다. 내부 self-check 같은 보조 섹션도 네 필수 섹션 뒤에 둘 수 있다.

### 역할
호출이 수행하는 작업 하나만 정의한다.

### 입력 경계
어떤 필드와 문맥만 입력 데이터로 사용하는지 정의한다. user message, 공고, README, transcript 등 외부 텍스트가 system 지시가 아니라 데이터임을 구분할 기반이 된다.

### 출력 계약
JSON Schema, 필드, 길이, 개수, 언어 등 서버가 검증할 결과 형식을 정의한다.

### 안전 경계
입력 안의 규칙 변경·prompt injection을 실행하지 않고, 제공되지 않은 사실·경험·성과를 만들지 않는 등 호출별 금지 행동을 정의한다.

## 현재 적용 대상

| 호출 | system Prompt | 상태 |
| --- | --- | --- |
| GitHub README 분석 | `prompts/github-readme-analysis.md` | 표준 4섹션 |
| 공고 요구사항 분석 | `prompts/job-requirement-analysis.md` | 표준 4섹션 |
| 비교 후 면접 대화 | `prompts/interview-conversation.md` | 표준 4섹션 |
| Skill-owned 코칭 후보 | `prompts/coaching-v5-skill-owned.md` | 표준 4섹션 |
| 채용 검색 의도 분류 | `JobSearchIntentService` inline Prompt | 표준 4섹션 |
| 질문 rubric 생성 | `_generation_prompt()` | 표준 4섹션 |
| 답변 rubric 평가 | `_evaluation_prompt()` | 표준 4섹션 |
| 예시 답변 생성 | `_example_answer_prompt()` | 표준 4섹션 |

## 예외: 현재 배포 v4 코칭 Prompt

`prompts/coaching.md`는 현재 배포 v4 재현 기준과 연결된 **동결 운영 snapshot**이다. 이 파일에 섹션 heading만 추가해도 Prompt hash와 기존 반복평가 기준이 달라지므로 이번 정리에서는 수정하지 않는다.

따라서 현재 상태를 다음처럼 구분한다.

- **신규/수정 가능한 system Prompt:** 표준 4섹션을 강제한다.
- **배포 v4 frozen snapshot:** 기존 구조를 보존한다.
- 다음 production 후보는 `coaching-v5-skill-owned.md` 구조를 사용해 재평가한 뒤 승격한다.

이 예외 때문에 “현재 배포 Prompt까지 모두 표준 4섹션으로 전환됐다”고 주장하지 않는다.

## system Prompt가 아닌 호출

Saramin/JobKorea web-search query는 외부 검색 도구에 전달하는 검색어이며 별도 LLM system Prompt 호출이 아니다. 검색 질의 데이터 경계는 해당 서비스의 query 생성·후처리 정책으로 관리하고 이 문서의 system Prompt 섹션 계약 대상에서는 제외한다.

## 회귀 검증

`backend/tests/test_system_prompt_sections.py`는 다음을 확인한다.

- mutable Prompt template 4개가 표준 4섹션을 정확히 한 번씩, 정해진 순서로 포함
- question rubric의 inline system Prompt 3개가 동일 계약을 준수
- job-search intent system Prompt가 동일 계약을 준수하고 사용자 메시지는 user data 구획에만 남음
- `coaching.md`는 의도적으로 frozen 예외임을 명시적으로 검사
