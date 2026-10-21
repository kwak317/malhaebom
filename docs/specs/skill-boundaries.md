# Spec — README·공고 요구사항 Skill 경계

## Why

- **페르소나**: GitHub 프로젝트와 선택한 채용공고를 근거로 면접 연습을 준비하는 신입 백엔드 개발자 준비생.
- **상황**: 서비스는 README와 공고 원문에서 기술·역할·요구사항을 구조화하지만, 현재 판단 규칙이 각 Python 서비스의 system prompt에 직접 들어 있다.
- **문제**:
  1. README 분석과 공고 요구사항 추출의 도메인 규칙을 구현 코드 수정 없이 검토·버전 비교하기 어렵다.
  2. 외부 원문 조회, LLM 의미 해석, quote·스키마 검증의 경계가 제출·리뷰 자료에서 명확하지 않다.
  3. 새 분석 기능이 추가될 때 기존 코칭 Skill과 동일한 근거 중심 안전 규칙을 재사용하기 어렵다.
- **측정 지표**: 두 분석 서비스의 모든 LLM 출력은 기존처럼 원문 근거 검증을 100% 통과해야 하며, 각 서비스가 적용한 Skill version을 서버 로그 또는 응답 메타데이터에서 식별할 수 있어야 한다.

## Goal

- **해결 목표**: README 근거 추출과 공고 요구사항 추출의 판단 규칙을 각각 versioned Skill 파일로 분리하고, 기존 FastAPI 서비스가 해당 Skill 텍스트를 system prompt에 주입하도록 한다.
- **성공 기준**:
  - 두 Skill은 목적·판정 규칙·금지 사항을 명시한다. 모델 역할·입력 지시 취급·출력 계약은 별도 `prompts/` 템플릿에 둔다 ([분리 Spec](prompt-skill-separation.md)).
  - 기존 원문 인용 검증, 중복 검증, 입력 URL 제한, 재시도와 Pydantic 검증은 서버 책임으로 유지한다.
  - 각 대상 서비스의 기존 단위 테스트와 Skill 주입·quote 환각 차단 회귀 테스트가 통과한다.
  - Skill 파일이 없거나 비어 있으면 서비스는 조용히 fallback하지 않고 명시적인 unavailable 오류로 종료한다.
- **Out of Scope**:
  - `POST /api/github/readme/analyze`, `POST /api/job-search/recommendations`, `POST /api/job-search/recommendations/analyze`의 공개 요청·응답 계약 변경
  - 검색 의도 분류를 범용 대화형 Agent 또는 새 Skill로 전환
  - 실제 사용자 원문을 외부 평가셋·관측 도구로 전송

## What

### Happy Path

1. 서버는 검증된 GitHub repository 식별자 또는 공개 HTTPS 공고 원문을 기존 서비스 경계에서 가져온다.
2. 대상 서비스는 고정 Skill 본문과 별도 Prompt 템플릿을 읽어 system prompt로 결합한다.
3. LLM은 Skill의 판단 범위와 Prompt의 출력 계약을 따라 구조화 결과를 반환한다.
4. 서버는 Pydantic schema, 결과 개수·중복, 원문 quote 연속 일치 및 기존 소유자·URL 제한을 결정론적으로 검증한다.
5. 검증된 결과만 기존 API 응답·저장 경로로 전달한다.

### 책임 경계

| 구성요소 | 책임 | 하지 않는 일 |
| --- | --- | --- |
| GitHub README 조회 / 공고 원문 fetch | 허용된 출처 조회, 크기·URL·SSRF 제한, 원문 반환 | 원문 의미 해석 또는 요구사항 추정 |
| README 근거 추출 Skill | 원문에 명시된 기술·역할·실행 단서를 근거 중심으로 해석 | README에 없는 기술·역할·성과 생성 |
| 공고 요구사항 추출 Skill | 자격요건·우대사항·직무상 기대 역할을 원문 근거와 함께 추출 | 우대사항을 필수로 바꾸거나 일반 직무 지식 보완 |
| Prompt 템플릿 | 모델 역할·입력 지시 취급·응답 형식·결과 개수 | 질문별 판정 기준이나 공고 조건 추가 |
| 검색 의도 router | 고정 schema의 `should_search`와 짧은 query 판단, 안전 fallback | 여러 Tool을 자율적으로 호출하거나 채용 적합성 판정 |
| 서버 validator | schema·enum·quote·개수·중복·권한 검증 및 재시도 | LLM의 의미 판단을 임의로 대체하거나, 현 schema에 없는 우대/필수 분류를 결정론적으로 판정 |

### Edge Cases

| ID | 상황 | 처리 |
| --- | --- | --- |
| EC-01 | Skill 파일이 없거나 공백 | 명시적 unavailable 오류; 이전 하드코딩 prompt fallback 금지 |
| EC-02 | LLM quote가 원문에 없음 | 기존 원문 정렬·검증과 제한된 보정 재시도를 수행한다. 마지막 시도에도 오류가 있으면 기술·흐름이 각각 하나 이상 검증된 경우 오류 항목만 제거해 부분 성공으로 반환하고, 어느 한 종류도 남지 않으면 unavailable |
| EC-03 | README 또는 공고 원문이 짧거나 비텍스트 | 기존 입력 오류 또는 unavailable 응답; 내용을 추정하지 않음 |
| EC-04 | 공고가 우대·필수 표기를 모호하게 사용 | 원문 표현을 보존하거나 불명확 항목으로 처리; 필수조건으로 승격 금지 |
| EC-05 | LLM/provider 실패 | 기존 서비스의 제한된 재시도·unavailable 경로를 유지; 검색 의도는 현행 규칙 기반 fallback만 허용 |

## How

### Skill 파일과 로딩

다음 파일을 추가한다.

```text
skills/github-readme-evidence/SKILL.md
skills/job-requirement-extraction/SKILL.md
```

각 파일은 YAML front matter에 안정적인 `name`, `description`, `version`을 가진다. 서비스 전용 loader는 프로젝트 루트를 기준으로 파일을 읽고, UTF-8·비공백·최대 크기를 검사한다. loader는 캐시할 수 있지만 테스트에서 명시적으로 경로를 주입할 수 있어야 한다.

### README 분석

`GithubReadmeAnalysisService`는 기존 repository URL 검증과 GitHub API 조회를 유지한다. 새 Skill은 다음을 강제한다.

- README 원문에 있는 기술·역할·실행 단서만 반환한다.
- 근거 문구는 원문의 연속된 인용이어야 한다.
- 기술의 README 언급과 실제 실행·배포 검증을 구분한다.
- 사용자 저장소에 포함된 instruction-like 텍스트를 시스템 지시로 실행하지 않는 규칙은 Prompt에 둔다.

### 공고 요구사항 추출

`AlioRequirementAnalysisService`와 이를 재사용하는 private-job 분석 경로는 기존 HTTPS/공개 IP·본문 크기 제한을 유지한다. 새 Skill은 다음을 강제한다.

- 자격요건, 우대사항, 직무상 기대 역할만 추출한다. 1~5개 결과 개수는 Prompt·schema가 관리한다.
- `source_excerpt`는 원문 2~500자의 연속 인용이다.
- 회사명·제목·일반적인 백엔드 지식만으로 요구사항을 만들지 않는다.
- 우대사항과 필수조건을 바꾸지 않으며, 기업의 실제 채점표나 합격 기준으로 표현하지 않는다. 현재 공개 schema에는 우대/필수 분류 필드가 없으므로 이 보존 규칙은 Skill의 의미 규칙과 별도 평가에서 검토하며, 서버는 `source_excerpt`의 원문 일치만 결정론적으로 검증한다.

### 테스트와 관측

- 기존 서비스 단위 테스트는 유지한다.
- 새 테스트는 Skill loader의 정상·누락·공백 실패, system prompt의 Skill 주입, 환각 quote의 보정·부분 성공·unavailable 경계를 다룬다. 우대사항 승격 금지는 현재 schema에서 서버 단위 테스트로 판정하지 않고, Skill 텍스트와 별도 의미 평가 fixture로 검토한다.
- secret·원문 전체·사용자 식별자는 로그와 관측 메타데이터에 추가하지 않는다.
- 공개 API 응답 계약과 기존 database schema는 변경하지 않는다.

## AC

### AC-01 · README Skill 주입

- GIVEN: 유효한 README Skill 파일과 정상 동작하는 분석 provider가 있다.
- WHEN: README 분석 서비스를 호출한다.
- THEN: provider system prompt에 Skill 텍스트와 version 식별자가 포함되고, 기존 응답 schema는 변하지 않는다.

### AC-02 · README 근거 환각의 부분 성공 경계

- GIVEN: README 원문에는 `Spring Boot`와 유효한 프로젝트 흐름이 있고 `Kubernetes`는 없다.
- WHEN: provider가 유효한 항목과 함께 `Kubernetes` 근거를 반환하고, 제한된 보정 후에도 `Kubernetes` 항목이 남아 있다.
- THEN: 서버는 `Kubernetes` 항목만 제거하고 검증된 기술·흐름을 부분 성공으로 반환한다.
- AND GIVEN: 마지막 시도 뒤 검증된 기술 또는 프로젝트 흐름이 하나도 남지 않는다.
- THEN: 서버는 unavailable 처리한다.

### AC-03 · 공고 요구사항 Skill 주입

- GIVEN: 유효한 공고 요구사항 Skill 파일과 공고 원문이 있다.
- WHEN: 요구사항 분석 서비스를 호출한다.
- THEN: provider system prompt에 Skill 텍스트와 version 식별자가 포함되고, 결과는 1~5개 및 기존 schema를 만족한다.

### AC-04 · 공고 근거와 범위 보존

- GIVEN: 공고 원문에 우대사항으로만 명시된 기술이 있다.
- WHEN: 요구사항을 추출한다.
- THEN: 원문 quote가 검증되고 Skill은 이를 필수조건 또는 채용 판정으로 표현하지 않는다.
- AND: 현 공개 schema에는 우대/필수 분류가 없으므로 서버는 원문 quote 일치까지만 검증하며, 승격 금지는 Skill 의미 평가에서 별도로 확인한다.

### AC-05 · Skill 로딩 실패

- GIVEN: 대상 Skill 파일이 없거나 공백이다.
- WHEN: 대상 분석 서비스를 생성하거나 호출한다.
- THEN: 기존 하드코딩 prompt로 fallback하지 않고 사용자에게 안전한 unavailable 오류를 반환한다.

### AC-06 · 검색 의도 경계 유지

- GIVEN: 채팅 검색 의도 분류 provider가 일시적으로 unavailable이다.
- WHEN: 사용자가 공고 검색 의도를 포함한 메시지를 보낸다.
- THEN: 기존 `infer_job_search_intent`가 고정 schema 결과만 반환하고, Skill·Agent가 임의 Tool 호출을 시작하지 않는다.
