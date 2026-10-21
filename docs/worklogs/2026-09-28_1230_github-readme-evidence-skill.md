# Worklog — README 근거 추출 Skill

- 일시: 2026-09-28 12:30 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: PR #84 (Skill 경계 Spec·계획), README Skill 구현 PR은 본 커밋 후 생성
- 관련 요구사항/결정: `docs/specs/skill-boundaries.md`, `docs/superpowers/plans/2026-09-28-analysis-skills.md`

## 1. 목적

기존 GitHub README 분석 서비스의 판단 규칙을 versioned Skill 파일로 분리하면서, 기존 공개 API와 서버의 원문 근거 검증을 유지한다.

## 2. 작업 전 상태

- `GithubReadmeAnalysisService`는 GitHub URL 제한, README 크기 제한, provider 재시도, Pydantic schema와 원문 excerpt 검증을 수행했다.
- 시스템 prompt의 판단 규칙은 `github_readme_analysis.py`에 직접 작성돼 있었고 별도 Skill 파일·version은 없었다.
- `backend/tests/test_github_readme_analysis.py` 12개가 로컬 가상환경에서 통과했다.

## 3. 수행 내용

1. UTF-8·frontmatter·비공백·placeholder·크기를 검증하고 SHA-256을 계산하는 공용 `analysis_skill` loader를 추가했다.
2. `github-readme-evidence-v1` Skill을 추가해 원문 명시 사실·연속 excerpt·개인 기여 추정 금지·실행 검증 주장 금지를 고정했다.
3. README 분석 서비스가 생성 시 Skill을 한 번 로드하고, version과 Skill 전문을 provider system prompt에 주입하도록 변경했다.
4. loader 오류는 파일 경로를 노출하지 않는 `GithubReadmeAnalysisUnavailable`로 변환했다.
5. versioned Skill 주입과 누락 Skill unavailable 회귀 테스트를 추가했다.
6. frontmatter만 있는 빈 Skill 본문을 시작 전에 차단하고, 각 README 분석 요청에 적용한
   Skill version만 서버 로그로 남기도록 보정했다. README 분석 규칙은 user prompt에서
   제거해 versioned Skill을 단일 기준으로 유지했다.

## 주요 판단과 이유

- Tool/서버 경계는 변경하지 않았다. GitHub fetch, URL 검증, quote 검사와 provider 재시도는 기존 서비스 책임으로 유지했다.
- Skill loader는 공고 요구사항 추출 서비스도 재사용할 수 있게 분석 서비스 전용의 작은 공용 모듈로 만들었다.
- 기존 테스트가 개인 기여 단정 금지 문구를 provider 입력 계약으로 확인하고 있어, 동등하지만 다른 Skill 문구 대신 기존 문구를 유지했다.
- 공개 API 응답 계약은 유지했다. Skill 전문이나 README 원문·URL은 로그에 넣지 않고
  `skill_version`만 요청마다 기록해 실제 적용 버전을 식별한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `skills/github-readme-evidence/SKILL.md` | README 근거 추출 판단 규칙과 version 정의 |
| `backend/app/services/analysis_skill.py` | 검증된 versioned Skill loader |
| `backend/app/services/github_readme_analysis.py` | Skill 로딩·system prompt 주입·오류 매핑 |
| `backend/tests/test_github_readme_analysis.py` | loader와 README Skill 통합 회귀 테스트 |
| `docs/worklogs/2026-09-28_1230_github-readme-evidence-skill.md` | 실제 변경·검증·미확인 상태 기록 |

## 5. 검증

```text
초기 시도: python -m pytest backend/tests/test_github_readme_analysis.py -q
결과: 전역 Python에 pytest가 없어 실행 불가.

초기 시도: python backend/tests/test_github_readme_analysis.py -q
결과: 전역 Python에 httpx가 없어 실행 불가.

실행 환경 보정: 프로젝트 루트 .venv + PYTHONPATH=<project root>

.venv\Scripts\python.exe backend/tests/test_github_readme_analysis.py -q
결과: 16 tests, OK

.venv\Scripts\python.exe backend/tests/test_practice_setup.py -q
결과: 13 tests, OK

초기 구현 시점의 전체 백엔드 단위 테스트는 종료 코드 0이었다. 이후 최신 main 기준으로
동일 명령을 다시 실행했을 때는 441 tests 중 1 failure, 37 errors로 실패했다.
- 대부분의 error: 실행 환경에 `tzdata`가 없어 `ZoneInfo("Asia/Seoul")`를 만들지 못함
  (공고 검색 관련 기존 테스트).
- failure: `test_evaluation_records`의 provider timeout/error 기대값 불일치.
- 위 항목은 README Skill 변경 범위 밖이므로 수정하지 않았다.

독립 코드리뷰 후 추가 회귀:
- `OPENROUTER_API_KEY`가 있고 README Skill loader가 실패하는 상태에서 앱 생성 성공, `/health` 200,
  인증된 `/api/github/readme/analyze` 503을 검증했다.
- `.venv\Scripts\python.exe backend/tests/test_github_readme_analysis.py -q`: 17 tests, OK
```

## 6. 발견한 문제 / 남은 리스크

- 현재 전역 Python에는 pytest와 백엔드 의존성이 설치돼 있지 않다. 테스트는 저장소 루트 `.venv`와 프로젝트 루트 `PYTHONPATH`를 명시해야 실행됐다.
- 기존 테스트는 system prompt의 개인 기여 금지 문구를 정확히 비교한다. Skill version 변경 시 이 안전 계약을 삭제하거나 다른 의미로 약화하지 않도록 주의가 필요하다.

## 미확인 사항

- 실제 GitHub API와 실제 provider를 포함한 E2E는 수행하지 않았다. 단위 테스트는 fake GitHub response와 fake provider만 사용했다.
- Skill version을 API 응답 또는 관측 메타데이터에 별도 노출하는 변경은 이번 범위에 포함하지 않았다.

## 리뷰 후 보정

- 독립 리뷰에서 loader 실패가 `create_app()` 전체를 중단할 수 있다는 P1을 발견했다.
- `build_github_readme_analysis_service_from_env()`가 생성 중 발생한 unavailable 오류를
  `UnavailableGithubReadmeAnalysisService`로 격리하도록 보정했다.
- 앱 health는 계속 제공하고 README endpoint만 503을 반환하는 RED→GREEN 회귀 테스트를 추가했다.

## 리뷰 후 보정 2

- frontmatter 종료 뒤 본문이 없는 파일도 기존 loader가 비공백 파일로 받아들이는 것을
  재현하는 RED 테스트를 추가했다.
- loader가 본문 규칙의 비공백 여부를 별도로 검사하도록 수정했고, 요청마다 적용한
  `github-readme-evidence-v1`을 서버 로그에 기록하는 회귀 테스트를 추가했다.
- README 인용·개인 기여 추정 금지 규칙은 `SKILL.md`가 소유하므로, 동일 규칙을 반복하던
  user prompt에서는 제거했다.
- `C:\\Users\\home\\Desktop\\proj2-3\\.venv\\Scripts\\python.exe`
  `backend/tests/test_github_readme_analysis.py -q`: 19 tests, OK.
- 전체 `unittest discover -s backend/tests -q`는 443개 중 1 failure와 37 errors로 실패했다.
  실패 원인은 기존 `tzdata` 미설치로 인한 `ZoneInfo("Asia/Seoul")` 오류 37건 및
  `test_evaluation_records`의 `timeout`/`provider_error` 기대값 불일치 1건이며,
  이번 README Skill 변경 파일과는 무관하다.

## 7. 다음 작업

- README Skill PR을 리뷰받는다.
- 승인·merge 뒤 최신 main에서 공고 요구사항 추출 Skill을 별도 브랜치·PR로 구현한다.
