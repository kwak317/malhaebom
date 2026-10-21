# Worklog — PR policy check rerun on description edit

- 일시: 2026-09-22 11:20 KST
- 작업자/에이전트: ChatGPT
- 관련 이슈/PR: PR #44 stale check 상태 조사 후 개선
- 관련 요구사항/결정: `docs/specs/pr-policy-rerun.md`, `docs/DECISIONS.md`의 PR Review-size 정책

## 1. 목적

PR description 수정으로 동일 HEAD에 과거 실패와 최신 성공 `PR Policy Check`가 별도 run으로 함께 남아 GitHub UI와 자동 도구가 stale 실패를 현재 실패로 오해하는 문제를 줄인다.

## 2. 작업 전 상태

- `.github/workflows/pr-policy-check.yml`이 `pull_request.edited`를 직접 구독했다.
- description을 수정할 때마다 동일 HEAD에 새 policy workflow run이 생성됐다.
- 정책 workflow는 이벤트 payload의 `github.event.pull_request.body`를 직접 파일로 써서 검사했다.
- PR #44에서 rationale 추가 전 FAILURE와 추가 후 SUCCESS가 별도 run으로 공존하는 사례를 확인했다.

## 3. 수행 내용

1. `docs/specs/pr-policy-rerun.md`에 자동 재실행 동작과 AC를 먼저 정의했다.
2. 본 `PR Policy Check`에서 `edited` trigger를 제거하고 `opened/synchronize/reopened`만 유지했다.
3. 본 정책 workflow가 매 실행/재실행 attempt마다 GitHub API에서 최신 PR description을 읽도록 변경했다.
4. PR 번호 + HEAD SHA 기반 policy `concurrency`와 `cancel-in-progress`를 추가했다.
5. `pr-policy-rerun-on-edit.yml` helper를 추가했다. description edit 시 현재 HEAD의 기존 policy run을 찾고 완료 후 Actions rerun API를 호출한다.
6. 연속 edit는 helper concurrency로 이전 helper를 취소하고, fork PR에서는 write-token rerun을 실행하지 않도록 제한했다.
7. workflow 계약을 정적 검증하는 `backend/tests/test_pr_policy_workflows.py`를 추가하고 본 policy CI에서 함께 실행하도록 연결했다.
8. `CURRENT_STATE.md`, `DECISIONS.md`에 동작과 판단을 반영했다.
9. PR #48 리뷰에서 edit helper가 HEAD A를 기다리는 동안 새 commit B가 들어오면 A rerun이 B policy check를 취소할 수 있는 race를 확인했다.
10. helper가 rerun 직전에 현재 PR HEAD를 다시 조회해 달라졌으면 obsolete rerun을 건너뛰도록 수정했고, policy concurrency key에도 HEAD SHA를 포함해 A/B가 서로 취소하지 못하도록 보강했다.
11. HEAD 재조회 → mismatch skip → rerun 순서를 고정하는 contract regression test를 추가했다.

## 주요 판단과 이유

- description edit마다 새 policy run을 생성하는 대신 기존 run의 새 attempt를 사용해 같은 HEAD의 stale 실패/성공이 독립 체크로 누적되는 것을 피한다.
- rerun은 원 이벤트 payload를 재사용할 수 있으므로 policy workflow가 현재 PR body를 API로 다시 읽어야 한다.
- 새 commit은 HEAD가 바뀌므로 기존처럼 새 policy run을 생성하는 것이 맞다.
- edit helper는 처음 받은 HEAD SHA를 끝까지 신뢰하면 안 된다. polling 중 새 commit이 들어올 수 있으므로 rerun 직전 현재 PR HEAD를 다시 확인한다.
- policy concurrency를 PR 번호만으로 공유하면 obsolete A rerun이 최신 B policy run을 취소할 수 있으므로 PR+HEAD 단위로 분리한다.
- helper가 성공/실패 여부와 관계없이 전체 기존 run을 rerun해야, 성공 후 rationale을 삭제한 경우도 다시 실패로 판정할 수 있다.
- 이미 과거에 생성된 workflow run을 삭제하는 작업은 이번 범위에 포함하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `.github/workflows/pr-policy-check.yml` | edited 제거, 최신 PR body 조회, concurrency, workflow 테스트 실행 |
| `.github/workflows/pr-policy-rerun-on-edit.yml` | description edit 시 기존 policy run 자동 rerun |
| `backend/tests/test_pr_policy_workflows.py` | trigger/API/rerun/concurrency 계약 테스트 |
| `docs/specs/pr-policy-rerun.md` | Why/Goal/What/How/AC |
| `docs/CURRENT_STATE.md` | 현재 CI 재실행 동작 기록 |
| `docs/DECISIONS.md` | 기존 run attempt 재사용 결정 추가 |

## 5. 검증

```text
python backend/tests/test_pr_policy_check.py
Ran 6 tests — OK

python backend/tests/test_pr_policy_workflows.py
Ran 3 tests — OK
```

## 6. 발견한 문제 / 남은 리스크

- 실제 GitHub Actions의 `GITHUB_TOKEN`으로 기존 workflow run rerun API가 동작하는지는 push/PR 후 원격에서 최종 확인이 필요하다.
- helper는 정책 run이 완료되기까지 최대 60초 polling한다. 정책 job이 60초보다 오래 걸리는 환경에서는 대기 한도를 조정해야 한다.
- c2c의 `statusCheckRollup` 단순 합산 로직은 별도 저장소 문제이며 이번 proj2-3 변경 범위에는 포함하지 않았다.

## 미확인 사항

- 실제 description edit → helper → 기존 run Attempt 2 생성 → 최신 body 반영까지의 GitHub UI E2E.
- fork PR에서 자동 rerun 대신 helper job skip이 기대대로 표시되는지.

## 7. 다음 작업

- 변경사항을 commit/push해 PR을 만든 뒤, 해당 PR description을 수정해 실제 rerun attempt와 Checks UI를 확인한다.
- 원격 E2E 성공 후 필요하면 c2c의 stale status-check 집계도 별도 수정한다.
