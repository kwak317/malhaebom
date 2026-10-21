# Worklog — PR 크기 정책 및 에이전트 Preflight 규칙 개선

- 일시: 2026-09-21 12:45
- 작업자/에이전트: Antigravity
- 관련 이슈/PR: chore/pr-size-policy-and-preflight
- 관련 요구사항/결정: 2026-09-21 PR 크기 정책을 Review Core 중심 가이드라인으로 개선

## 1. 목적

- 기존 `AGENTS.md`의 "human-authored diff 400줄 이하" 무조건적 hard limit으로 인해 발생하던 기계적/인위적 PR 과도 분할 문제 해결.
- PR 400줄 기준을 "리뷰 가능한 변경 크기(Review Core)" 중심으로 현실화하고 예외 파일(Worklog, 실험기록, lockfile 등)을 분리.
- `AGENTS.md` 상단에 `Mandatory Preflight` 섹션을 추가해 작업 시작 시 핵심 원칙을 즉시 인지하도록 개선.
- 문서에만 두지 않고 diff 크기 및 Review Core를 판정하는 `scripts/check_pr_policy.py` 및 CI workflow를 구축.
- PR 템플릿(`.github/PULL_REQUEST_TEMPLATE.md`)을 정비해 Review-size 분석 및 초과 사유를 리뷰어가 바로 볼 수 있게 함.

## 2. 작업 전 상태

- `AGENTS.md` 제10절에 "원칙적으로 human-authored diff는 400줄 이하로 유지한다"는 규칙이 있었으나, Spec/Worklog/실험결과 등 필수 문서가 포함되어 전체 465줄이 된 경우(예: PR #19)에도 기계적으로 쪼개야 하는 딜레마가 발생함.
- 핵심 작업 규칙이 문서 중간/후반에 위치하여 AI 에이전트가 작업 전 놓치기 쉬움.
- PR 크기나 Review Core를 자동으로 판정하는 도구나 CI 검사가 없음.
- `.github/` 아래에 `PULL_REQUEST_TEMPLATE.md`와 `pull_request_template.md` 두 개가 혼재되어 있었음.

## 3. 수행 내용

1. **`AGENTS.md` 구조 개선**:
   - 최상단에 `## Mandatory Preflight (작업 시작 시 필수 확인)` 신설 (6대 원칙 요약 및 본문 링크).
   - 제10절(PR·리뷰·merge 규칙)을 개정하여 `400 LOC`를 review-size guideline으로 정의하고 Review Core(코드/테스트/설정/핵심Spec) 개념 도입, 800줄 초과 시 분리 필수, 400~800줄은 PR description 사유 필수 작성 명시.
   - 제14절에 자동 기술적 검증(CI)과 문서 정책의 구분을 최신화.
2. **PR 정책 검증 스크립트 구현 (`scripts/check_pr_policy.py`)**:
   - `git diff --numstat` 분석을 통해 Review Core와 Exception(Worklog, 실험기록, lockfile 등)을 분리 집계.
   - Core <= 400: 통과.
   - Core 401 ~ 800: PR description에 사유/이유 기재 여부 확인 (미작성 시 실패).
   - Core > 800: 정책 위반으로 즉시 차단(하드 리밋).
3. **단위 테스트 추가 (`backend/tests/test_pr_policy_check.py`)**:
   - numstat 파싱, 예외 파일 판정, Core/Exception 분류, 400/800 경계값 및 PR 본문 사유 검증 단위 테스트 6건 작성 및 통과 확인.
4. **CI Workflow 구축 (`.github/workflows/pr-policy-check.yml`)**:
   - PR 열림/수정 시 가벼운 Python 3.12 환경에서 단위 테스트 및 diff 크기 검증 실행 (추가 ML dependency 다운로드 없음).
5. **PR 템플릿 단일화 및 고도화 (`.github/PULL_REQUEST_TEMPLATE.md`)**:
   - 중복된 소문자 템플릿 파일 삭제 및 대문자 템플릿으로 단일화.
   - 목적, 주요 변경, Review-size 분석, 기준 초과 사유, 검증 결과, 체크리스트 포함.
6. **기준 문서 동기화**:
   - `docs/CURRENT_STATE.md` 및 `docs/DECISIONS.md` 갱신.

## 주요 판단과 이유

- **기계적 분할 지양**: PR #19처럼 Review Core는 259줄이고 나머지가 Worklog/실험기록인 경우, 하나의 논리적 완결성을 가진 작업을 억지로 쪼개면 리뷰 컨텍스트가 깨지고 검증이 어려워진다.
- **경량 CI 유지**: PR 정책 검증을 위해 무거운 프레임워크나 외부 서비스 대신 Python 표준 라이브러리(`argparse`, `fnmatch`, `subprocess`, `unittest`)만 사용하여 CI 실행 시간을 수 초 이내로 유지함.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `AGENTS.md` | Mandatory Preflight 추가, PR review-size 원칙 개정, 문서 vs 기술적 강제 구분 갱신 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 목적, 변경사항, review-size 분석 및 사유, 검증 항목 보강 |
| `.github/pull_request_template.md` | 중복 템플릿 파일 삭제 (PULL_REQUEST_TEMPLATE.md로 단일화) |
| `.github/workflows/pr-policy-check.yml` | 경량 PR 정책 및 review-size 검사 GitHub Actions workflow 추가 |
| `scripts/check_pr_policy.py` | base...head diff 및 review core 분석, 사유 검사 스크립트 신설 |
| `backend/tests/test_pr_policy_check.py` | PR 정책 검사 스크립트 단위 테스트 (6개 케이스) |
| `docs/CURRENT_STATE.md` | PR 정책 개선 및 Preflight 검증 반영 현황 기록 |
| `docs/DECISIONS.md` | 2026-09-21 PR 크기 정책 가이드라인화 결정 기록 |
| `docs/worklogs/2026-09-21_1245_pr-size-policy-and-preflight.md` | 본 작업 Worklog |

## 5. 검증

```bash
# 1. 단위 테스트 실행
python3 -m unittest -v backend/tests/test_pr_policy_check.py
# Ran 6 tests in 0.004s, OK

# 2. PR #19 대상 정책 판정 시뮬레이션 (새 보수적 규칙: docs/experiments/** 문서도 Review Core 포함)
python3 scripts/check_pr_policy.py --base origin/main --head origin/pr/19
# Diff Summary:
#   - Total Diff: 466 lines (+460 / -6)
#   - Review Core Diff: 322 lines (+316 / -6)
#   - Exception Diff: 144 lines (+144 / -0)
# Top Review Core Files:
#   * evals/run_model_comparison.py: +104/-1 (105 lines)
#   * docs/experiments/2026-09-21_candidate-30case-extension.md: +63/-0 (63 lines)
#   * docs/specs/local-ollama-model-evaluation.md: +50/-0 (50 lines)
#   * EVAL_REPORT.md: +40/-5 (45 lines)
#   * backend/tests/test_coaching_eval.py: +35/-0 (35 lines)
# Top Exception Files:
#   * docs/worklogs/2026-09-20_1452_local-ollama-evaluation.md: +83/-0 (83 lines)
#   * docs/worklogs/2026-09-21_1020_candidate-30case-extension.md: +61/-0 (61 lines)
# [PASS] Review Core size (322 lines) is within recommended limit (400 lines).

# 3. 현재 작업 브랜치 자체에 대한 정책 검사
python3 scripts/check_pr_policy.py --base origin/main --head HEAD
# Total Diff: 608 lines (+584 / -24)
# Review Core Diff: 516 lines (+492 / -24)
# Exception Diff: 92 lines (Worklog 92 lines)
# [NOTICE] Review Core size is 516 lines (exceeds recommended guideline of 400 lines).
# [PASS] Documented rationale found in PR description.
```

## 6. 발견한 문제 / 남은 리스크

- 없음.

## 미확인 사항

- GitHub Actions 원격 저장소에서의 실제 workflow 트리거 동작 (PR push 후 GitHub 상에서 확인 예정).

## 7. 다음 작업

- 변경사항 commit 및 push 후 PR 생성.

