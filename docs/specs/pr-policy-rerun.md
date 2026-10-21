# PR 정책 검사 자동 재실행 Spec

## Why

- **상황**: PR Review Core가 400~800줄이면 PR description의 초과 사유와 비분리 이유를 검사한다.
- **문제**: 현재 `pull_request.edited`가 정책 workflow 자체를 새로 실행해, 같은 HEAD에 이전 실패 run과 최신 성공 run이 별도 체크로 함께 남는다.
- **영향**: GitHub Checks UI와 외부 도구가 과거 실패를 현재 실패처럼 집계할 수 있어 리뷰 판단을 혼동시킨다.
- **측정 지표**: PR 본문 수정 시 새 정책 run을 추가하지 않고 기존 정책 run의 새 attempt를 자동 실행한다.

## Goal

- PR 생성·재오픈·새 커밋에서는 정상적으로 새 `PR Policy Check` run을 실행한다.
- PR description 수정에서는 기존 HEAD의 최신 `PR Policy Check` run을 자동 rerun한다.
- rerun된 정책 검사는 이벤트 당시 본문이 아니라 GitHub API의 최신 PR description을 사용한다.
- 같은 PR의 불필요한 동시 정책 검사는 concurrency로 취소한다.
- **Out of Scope**: 과거에 이미 생성된 workflow run 삭제, GitHub branch protection 변경, 외부 실행 도구의 CI 상태 집계 로직 수정.

## What

**Happy Path**

1. PR이 생성되거나 새 commit이 push되면 `PR Policy Check`가 실행된다.
2. Review Core가 400줄을 넘고 rationale이 없으면 실패한다.
3. 작성자가 PR description에 rationale을 추가한다.
4. `edited` 전용 helper가 같은 HEAD의 기존 정책 run이 끝날 때까지 기다린다.
5. helper가 기존 run 전체를 rerun한다.
6. 새 attempt는 GitHub API에서 최신 PR description을 읽어 통과 여부를 다시 계산한다.

**Edge Cases**

| 상황 | 처리 |
| --- | --- |
| description 수정 시 정책 run이 아직 진행 중 | helper가 bounded polling 후 완료된 같은 HEAD run을 rerun한다. |
| 짧은 시간에 description을 여러 번 수정 | helper concurrency로 이전 helper를 취소하고 마지막 수정 기준으로 한 번만 rerun한다. |
| description 수정 직후 새 commit push | helper가 rerun 직전 현재 PR HEAD를 다시 읽고, edit 이벤트의 HEAD와 다르면 obsolete rerun을 건너뛴다. policy concurrency는 PR+HEAD 단위라 오래된 HEAD rerun이 새 HEAD 검사를 취소하지 못한다. |
| 같은 HEAD의 정책 run을 찾지 못함 | helper는 제한 시간 후 실패해 자동 재검사 누락을 드러낸다. |
| fork PR | write token 제약을 피하기 위해 helper rerun은 동일 저장소 branch에만 수행한다. |

## How

- `.github/workflows/pr-policy-check.yml`
  - `edited` trigger 제거.
  - `opened`, `synchronize`, `reopened` 유지.
  - PR 번호 + HEAD SHA 기반 concurrency + `cancel-in-progress: true`.
  - `pull-requests: read`, `contents: read` 권한 명시.
  - `gh api repos/{repo}/pulls/{number}`로 현재 PR body를 `/tmp/pr_body.txt`에 저장.
- `.github/workflows/pr-policy-rerun-on-edit.yml`
  - `pull_request: types: [edited]`.
  - 동일 저장소 branch에서만 실행.
  - `actions: write`, `contents: read`, `pull-requests: read` 권한.
  - 현재 PR HEAD SHA와 일치하는 `pr-policy-check.yml` run을 조회.
  - 완료될 때까지 제한적으로 polling한다.
  - rerun 직전에 PR API에서 현재 HEAD를 다시 조회하고 edit 이벤트 HEAD와 다르면 정상 종료한다.
  - HEAD가 여전히 같을 때만 `POST /actions/runs/{run_id}/rerun`.
  - PR 번호 기반 helper concurrency 적용.
- 정책 계산 자체(`scripts/check_pr_policy.py`)의 400/800 기준은 변경하지 않는다.

## AC

- **AC-01 · 본문 수정은 본 정책 workflow의 새 run을 직접 만들지 않음**
  - GIVEN: `pr-policy-check.yml`이 있다.
  - WHEN: trigger 구성을 검사한다.
  - THEN: `edited`는 없고 `opened/synchronize/reopened`만 포함한다.
- **AC-02 · 최신 PR description 사용**
  - GIVEN: 기존 workflow run이 다른 body payload로 시작했다.
  - WHEN: 정책 검사 attempt가 실행된다.
  - THEN: GitHub API에서 현재 PR body를 읽어 정책 스크립트에 전달한다.
- **AC-03 · edited 시 기존 run 자동 rerun**
  - GIVEN: 동일 저장소 PR description이 수정됐다.
  - WHEN: helper workflow가 실행된다.
  - THEN: 현재 HEAD의 기존 policy run을 찾고 Actions rerun API를 호출한다.
- **AC-04 · 중복 실행 억제**
  - GIVEN: 같은 PR에서 연속 commit 또는 description edit가 발생한다.
  - WHEN: 새 workflow/helper가 실행된다.
  - THEN: policy workflow는 PR+HEAD 단위 concurrency로 동일 HEAD 중복 실행만 취소하고, helper는 PR 번호 기반 concurrency로 연속 edit helper를 정리한다.
- **AC-05 · 새 HEAD가 들어온 뒤 obsolete rerun 금지**
  - GIVEN: description edit 이벤트가 HEAD A를 캡처했고 helper가 A의 policy run을 기다리는 동안 HEAD B가 push됐다.
  - WHEN: A run이 완료되어 helper가 rerun 직전 상태를 확인한다.
  - THEN: helper는 현재 PR HEAD B를 확인하고 A를 rerun하지 않은 채 성공 종료한다.
