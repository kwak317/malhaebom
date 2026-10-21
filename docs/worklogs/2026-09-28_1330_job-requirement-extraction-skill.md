# Worklog — 공고 요구사항 추출 Skill

- 일시: 2026-09-28 13:30 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: PR #84 (Skill 경계 Spec), PR #85 (README Skill 선행 구현)
- 관련 요구사항/결정: `docs/specs/skill-boundaries.md`, `docs/superpowers/plans/2026-09-28-analysis-skills.md`

## 1. 목적

기존 공고 요구사항 분석 서비스의 의미 판단 규칙을 versioned Skill 파일로 분리하면서, 기존 원문 fetch·근거 정렬·스키마 검증·재시도와 공개 API 계약을 유지한다.

## 2. 작업 전 상태

- `AlioRequirementAnalysisService`는 HTTPS/공개 IP 제한, 원문 크기 제한, provider 재시도와 `source_excerpt` 원문 정렬을 수행했다.
- 판단 규칙은 `_system_prompt()`에 직접 작성돼 있었고, 별도 Skill 파일과 version은 없었다.
- README Skill에서 도입한 `AnalysisSkillBundle` loader는 최신 `main`에 병합돼 있었다.

## 3. 수행 내용

1. `job-requirement-extraction-v1` Skill을 추가했다.
2. 서비스 생성 시 공용 loader로 Skill을 한 번 검증·로딩하고, version·전문을 provider system prompt에 주입하도록 변경했다.
3. 누락·공백·오류 Skill은 하드코딩 prompt로 fallback하지 않고 `AlioRequirementAnalysisUnavailable`로 바꿨다.
4. 환경 기반 service factory도 Skill 초기화 실패를 unavailable service로 격리해 앱 시작을 막지 않도록 했다.
5. versioned Skill 주입과 공백 Skill unavailable 회귀 테스트를 추가했다.

## 주요 판단과 이유

- 우대사항과 필수조건을 구분하는 공개 response field가 없으므로, 서버가 요구사항 `text`의 의미를 판정한다고 주장하지 않았다. 대신 Skill에 원문 표현 보존과 우대사항 승격 금지를 고정했다.
- 기존 서버의 quote 정렬·검증은 그대로 유지했다. 이는 원문에 없는 근거를 성공 응답으로 남기지 않는 결정론적 책임이다.
- 공고 제목·회사명·일반 직무 지식으로 새 조건을 만들지 않는 규칙은 Skill 판단 책임으로 유지했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `skills/job-requirement-extraction/SKILL.md` | versioned 요구사항 추출 규칙과 우대사항 보존 규칙 |
| `backend/app/services/alio_requirement_analysis.py` | Skill 로딩·system prompt 주입·초기화 실패 격리 |
| `backend/tests/test_alio_requirement_analysis.py` | Skill 주입과 공백 Skill unavailable 회귀 테스트 |
| `docs/worklogs/2026-09-28_1330_job-requirement-extraction-skill.md` | 변경·검증·미확인 상태 |

## 5. 검증

```text
실행 환경: 프로젝트 루트 .venv + PYTHONPATH=<project root>

.venv\Scripts\python.exe backend/tests/test_alio_requirement_analysis.py -q
결과: 11 tests, OK

.venv\Scripts\python.exe backend/tests/test_saramin_recommendation.py -q
결과: 35 errors. 가상환경에 `tzdata`가 없어 `ZoneInfo("Asia/Seoul")` 생성 전 실패했다.

.venv\Scripts\python.exe backend/tests/test_practice_setup.py -q
결과: 13 tests, OK

.venv\Scripts\python.exe -m unittest discover -s backend/tests -p 'test_*.py' -q
결과: 445 tests 중 1 failure, 37 errors.
- 37 errors: `tzdata` 누락으로 공고 검색·인천 채용 관련 테스트가 `Asia/Seoul` 생성에 실패했다.
- 1 failure: `test_evaluation_records`가 `provider_error`를 기대했지만 실제 `timeout`을 반환했다.
- 두 항목은 이 Skill 변경 범위 밖의 환경·기존 평가 동작 문제이므로 수정하지 않았다.
```

## 6. 발견한 문제 / 남은 리스크

- 현재 response schema에는 우대/필수 분류 필드가 없다. 따라서 우대사항의 필수조건 승격 금지는 Skill 텍스트와 후속 의미 평가에서 검토해야 하며, 이 서비스의 서버 테스트는 원문 quote 정합성만 보장한다.
- Skill version을 API 응답이나 관측 메타데이터에 별도 노출하는 변경은 이번 범위에 포함하지 않았다.

## 미확인 사항

- 실제 외부 공고 원문과 실제 provider를 포함한 E2E는 수행하지 않았다. 테스트는 fake source·provider를 사용한다.
- `tzdata`를 포함한 테스트 환경에서 공고 추천 및 전체 backend unittest discovery를 재실행할 필요가 있다.

## 7. 다음 작업

- PR 리뷰를 받는다.
- `tzdata` 환경 문제와 평가 provider failure 기대값 불일치를 별도 Issue 또는 범위가 분리된 작업으로 정리한다.
