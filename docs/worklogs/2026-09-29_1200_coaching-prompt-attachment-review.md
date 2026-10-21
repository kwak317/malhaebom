# Worklog — 첨부 코칭 시스템 프롬프트 검토

## 목적

첨부된 `message (1).txt`의 코칭 시스템 프롬프트 v0를 저장소의 canonical Prompt·Skill 구조와 대조하고, 필요한 수정 여부와 Git 이력을 확인한다.

## 작업 전 상태

- 작업 시작 시 `git status --short --branch`를 확인했다.
- 기존 작업 트리에는 별도 미커밋 변경이 없었다.
- 첨부 파일은 저장소에 추적되는 파일이 아니며, `malhaebom-coaching-v0` 미등록 검토 초안으로 표시되어 있었다.

## 확인 내용

- 저장소의 운영 기본 Prompt는 `coaching-output-v4.1`이다.
- 운영 fallback과 평가 runner는 `backend/app/services/coaching_prompt.py`의 동일한 canonical builder를 사용한다.
- Skill은 `skills/SKILL.md`, 질문별 문서, `skills/criteria.json`을 검증·조합하는 구조다.
- v0의 “Skill 파일·본문·로더를 불러오지 않는다”는 실행 구성은 현재 저장소의 Skill 런타임 계약과 충돌한다.
- v0에는 현재 v4.1에 있는 일부 보강 내용(예: `evidence` 키 고정, `text` 키 금지, 활성 criterion ID 제한, 출력 전 self-check)이 명시적으로 부족하다.
- 따라서 v0를 별도 파일이나 기본 Prompt로 추가하지 않았다. 추가하면 운영·평가 Prompt 버전이 분기되고 과거 평가 재현성도 훼손될 수 있다.

## Git에서 확인한 Prompt·Skill 동시 변경

Prompt/Skill 관련 파일이 함께 변경된 대표 커밋은 다음과 같다.

| 커밋 | 내용 | 함께 변경된 범위 |
|---|---|---|
| `678dfec` | canonical prompt repair harness 추가 | `coaching_prompt.py`와 코칭 테스트·런타임 |
| `0945463` | 원인 관찰/추론 기준 분리 | `skills/SKILL.md`, `problem-solving.md`, `criteria.json`과 런타임 계약 |
| `cf82ee0` | preset interview Skill catalog 추가 | `SKILL.md`, `criteria.json`, `preset-interview.md`, Skill loader와 테스트 |
| `b247e94` | 평가 정책 정렬 | `SKILL.md`, `problem-solving.md`, `criteria.json`과 평가 기반 |
| `bbeef8a` | 근거 기반 예시 답변 추가 | Prompt 출력 계약 관련 코드·테스트와 Skill 기준 |

추가로 `3b4bbe9`, `0eaac33`, `7a5b097`에서도 코칭 Skill과 런타임/검증 코드가 함께 변경되었다.

## 검증

- `backend/tests/test_coaching_prompt.py`
- `backend/tests/test_coaching_skill.py`

- `python -m pytest backend/tests/test_coaching_prompt.py backend/tests/test_coaching_skill.py`는 환경에 `pytest` 모듈이 없어 실행되지 않았다.
- `python -m unittest backend.tests.test_coaching_prompt backend.tests.test_coaching_skill`도 테스트 수집 단계에서 `pydantic` 모듈이 없어 실패했다.

## 미확인·다음 작업

- 첨부 v0를 Langfuse에 등록하거나 production label로 승격하지 않았다.
- 의존성 미설치로 테스트 통과를 확인하지 못했으므로 이번 검토를 코드 테스트 완료로 보고하지 않는다.
- 실제 모델 품질 개선 여부는 별도 동일 Dataset 평가 없이는 판단하지 않는다.
- v4.1을 변경하려면 먼저 새 Prompt spec과 비교 평가를 추가해야 한다.
