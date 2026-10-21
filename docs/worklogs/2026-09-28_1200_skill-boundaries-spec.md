# Worklog — README·공고 요구사항 Skill 경계 Spec

- 일시: 2026-09-28 12:00 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음 (후속 구현 PR 분리 예정)
- 관련 요구사항/결정: `docs/specs/skill-boundaries.md`, `docs/CONSTRAINTS.md`

## 1. 목적

이미 존재하는 README 분석·공고 요구사항 추출·검색 의도 분류를 Tool, Skill, router, 서버 validator 책임으로 명확히 나누고 후속 구현 범위를 고정한다.

## 2. 작업 전 상태

- 최신 main에는 GitHub README 분석, 공고 요구사항 추출, 공고 검색 의도 분류 endpoint와 서비스가 구현돼 있었다.
- README와 공고 분석의 판단 규칙은 서비스 내부 system prompt에 있었고, 코칭 Skill처럼 독립된 versioned Skill 파일로 분리돼 있지 않았다.
- 공고 원문 fetch의 HTTPS·공개 IP·크기 제한, Pydantic schema, quote 원문 검증·보정 재시도는 구현돼 있었다.

## 3. 수행 내용

1. `docs/specs/skill-boundaries.md`에 Why·Goal·What·How·AC를 작성했다.
2. README 근거 추출과 공고 요구사항 추출은 Skill, 외부 원문 조회는 Tool, 검색 의도는 router라는 책임 경계를 기록했다.
3. 현재 API 계약·원문 검증·SSRF 방어·RAG 제외 범위를 유지하도록 후속 구현 제약을 명시했다.
4. PR review 후 공개 schema가 제공하지 않는 우대/필수 분류를 서버가 보장한다고 읽힐 수 있던 표현을 수정했다. 해당 금지는 Skill 의미 규칙·별도 평가로, 서버는 quote 일치 검증으로 구분한다.
5. README 환각 quote는 기존 부분 성공 동작과 일치하도록, 유효한 기술·흐름이 각각 남으면 오류 항목만 제거하고 둘 중 하나가 남지 않을 때만 unavailable로 처리한다고 Spec·계획에 명시했다.

## 주요 판단과 이유

- 이미 동작하는 endpoint를 새 Agent로 재구축하지 않는다. 고정 판단 규칙만 versioned Skill로 분리하고, deterministic 검증은 서버에 남긴다.
- 검색 의도는 좁은 schema router 및 규칙 기반 fallback이 안전하므로 새 Skill로 만들지 않는다.
- 기존 `AlioAnalyzedRequirement`에는 분류 필드가 없으므로, Skill의 우대사항 보존 지시를 서버 validator가 의미적으로 판정한다고 표현하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/specs/skill-boundaries.md` | Skill/Tool/router/server validator 경계와 AC 정의 |
| `docs/worklogs/2026-09-28_1200_skill-boundaries-spec.md` | Spec 작성 근거·범위·미확인 사항 기록 |

## 5. 검증

```text
정적 확인:
- backend/app/services/github_readme_analysis.py의 기존 원문 조회·quote 검증 경로 확인
- backend/app/services/alio_requirement_analysis.py의 HTTPS/공개 IP/본문 제한·quote 검증 경로 확인
- backend/app/services/job_search_intent.py의 LLM 실패 시 규칙 기반 fallback 확인
- docs/specs/_example.md의 Why·Goal·What·How·AC 형식 대조
```

## 6. 발견한 문제 / 남은 리스크

- README/공고 서비스의 기존 prompt 규칙과 새 Skill 텍스트가 중복될 수 있다. 후속 구현에서는 canonical Skill을 하나로 정하고 service prompt에는 경계·계약만 남겨야 한다.

## 미확인 사항

- 실제 외부 provider를 포함한 README/공고 분석 E2E는 이번 문서 단계에서 수행하지 않았다.
- Skill version을 API 응답에 노출할지, redacted 관측 메타데이터에만 남길지는 후속 구현에서 현재 응답 호환성과 함께 결정한다.
- 우대/필수 분류를 공개 schema에 추가하고 서버에서 결정론적으로 검증하는 것은 이번 문서·후속 Skill 주입 범위에 포함하지 않는다.

## 7. 다음 작업

- README 근거 추출 Skill loader·주입·회귀 테스트를 별도 feature 브랜치에서 구현한다.
- 공고 요구사항 추출 Skill loader·주입·회귀 테스트를 별도 feature 브랜치에서 구현한다.

> 2026-10-04 사용자 요청으로 도메인 확장을 범위 밖으로 두는 문구를 삭제했다. 당시 수행·검증 기록은 현재 기능의 완료 증거로 확대하지 않는다.
