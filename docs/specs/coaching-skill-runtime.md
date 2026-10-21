# 코칭 Skill 런타임 계약 Spec

## Why

- PRD는 `SKILL.md`, 질문 유형 문서, `criteria.json`을 고정 입력으로 요구하지만 저장소에는 빈 Skill 템플릿만 있었다.
- Mock API와 평가셋이 서로 다른 기준 ID를 사용하면 같은 이름의 기능이 다른 규칙으로 판정된다.
- 문서만 추가하고 서버에서 버전을 확인하지 않으면 잘못된 질문 문맥이 모델 호출 단계까지 전달될 수 있다.

## Goal

- 문제 해결 질문의 팀 초안 기준을 하나의 Skill 묶음으로 고정한다.
- API, MCP, 평가 runner가 같은 기준 ID와 버전을 검증한다.
- 실제 모델을 정하기 전에도 Mock과 평가 계약을 재현할 수 있게 한다.

성공 기준은 빈 템플릿이 없는 Skill 묶음, 다섯 개 기준의 단일 ID 체계, 잘못된 질문 유형·기준·버전의 서버 차단, 평가 리포트의 Skill 묶음 해시 기록이다.

### Out of Scope

- 외부 면접관 검토 완료 선언
- 실제 후보 모델 선정과 성능 수치 확정
- RAG, 임베딩, 벡터 검색
- 이 Skill 로더·기준 ID 계약 작업에서 운영 공고 수집 경로를 변경하는 것. 제품 전체의 공고 수집·도메인 확장 범위는 [TARGET_STATE](../TARGET_STATE.md)를 따른다.

## What

### 고정 파일

| 파일 | 역할 |
|---|---|
| `skills/interview-coach/SKILL.md` | 모델이 따라야 할 입력 경계와 판정 절차 |
| `skills/interview-coach/problem-solving.md` | 문제 해결 질문 유형의 적용 규칙과 경계 사례 |
| `skills/interview-coach/criteria.json` | 기준 ID, 설명, 버전, 검토 상태의 기계 판독 계약 |
| `skills/interview-coach/rule-provenance.json` | criterion별 도입 이유·규칙 출처·전문가 검토 상태 추적 메타데이터 |

기준의 검토 상태는 `team_draft`다. 외부 검토가 끝나기 전에는 전문가 검증 기준으로 표현하지 않는다.
`rule-provenance.json`의 현재 33개 criterion은 모두 `expert_review.status=deferred`, `display_status=유보`로 두며 reviewer는 확정하지 않는다. 이 파일은 추적 메타데이터이고 모델 system prompt에는 합성하지 않는다.

## How

1. 서버 시작 또는 코칭 서비스 생성 시 세 파일을 읽고 JSON 구조, 파일 참조, 중복 ID를 검증한다.
2. 질문 조회 시 `question_type`, `criteria_version`, `active_criterion_ids`가 카탈로그와 맞는지 확인한다.
3. 평가 runner는 세 파일을 하나의 시스템 입력으로 구성하고 묶음 SHA-256을 결과에 기록한다.
4. 평가셋은 카탈로그에 있는 기준 ID만 사용한다.

## AC

- **AC-01**: Skill 폴더가 frontmatter와 필수 참조 파일을 포함하고 placeholder가 없다.
- **AC-02**: 기준 카탈로그에 `problem_context`, `cause_observation`, `cause_inference`, `own_action`, `action_rationale`, `result_verification`가 한 번씩 존재한다.
- **AC-03**: 알 수 없는 질문 유형·기준 ID 또는 다른 기준 버전은 LLM 호출 전에 거부된다.
- **AC-04**: 평가셋 30건의 활성 기준과 기대 판정 ID가 카탈로그 범위 안에 있다.
- **AC-05**: 모델 비교 결과에 prompt, Skill, criteria 버전과 Skill 묶음 해시가 기록된다.
- **AC-06**: 외부 검토와 실제 모델 측정이 완료된 것처럼 문서에 표시하지 않는다.
- **AC-07**: result_verification에서 확인·테스트 행위와 실제 관찰 결과를 구분한다. "~인지 확인했다"처럼 확인 행위만 있고 실제 결과가 명시되지 않으면 partial로 유지한다.
- **AC-08**: intent와 C/A/V는 독립 판정한다. 비백엔드 경험도 답변 자체에 문제·개인 행동·확인 결과가 있으면 해당 C/A/V 기준을 충족할 수 있다.
