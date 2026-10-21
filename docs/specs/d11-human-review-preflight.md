# D11 신규 인젝션 사람 검토 preflight

## Why

- **페르소나**: D11 평가셋을 검토·승인하는 팀원 또는 독립 검토자.
- **상황**: 신규 인젝션 후보 3건은 LLM 초안과 사용자 label 승인으로만 존재한다.
- **문제**: 후보를 바로 공식 정답으로 사용하면 입력과 정답의 독립 근거가 사라진다.
- **측정 지표**: 공식 Dataset으로 승격되기 전 사람 검토 필수 필드 누락 0건.

## Goal

- **해결 목표**: 후보 3건의 사람이 채울 검토 패킷을 offline으로 생성한다.
- **성공 기준**: 정확히 3개의 고유 후보, 모든 사람 판정 필드는 빈값, provider 호출 0회, 공식 Dataset 갱신 권한 false.
- **Out of Scope**: 사람 판정 대행, official Dataset 갱신, 모델 호출·유료 평가, before/after 측정.

## What

**Happy Path**: 후보 JSONL을 읽어 `local-results/` 아래에 검토 Markdown과 빈 JSON template을 생성한다.

**Edge Cases**:

| 상황 | 처리 |
| --- | --- |
| 후보 수 또는 ID가 3개가 아님 | 생성 중단 |
| 독립 사람 검토 대기 provenance가 없음 | 생성 중단 |
| 출력 경로가 `local-results/` 밖 | CLI 오류 |
| 출력 폴더가 이미 존재 | 덮어쓰지 않고 CLI 오류 |

## How

- 입력: `evals/d11_injection_candidates.jsonl`.
- 출력: git-ignored `local-results/<run>/REVIEW.md`, `human-review.template.json`.
- 2026-10-08 인계 기본 출력: `local-results/d11-injection-review-20261008/` (`--output-dir` 생략 시). 같은 디렉터리가 있으면 덮어쓰지 않고 중단한다. 별도 경로로 재생성하려면 `--output-dir local-results/<new-run>`을 명시한다.
- template 필수 사람 입력: reviewer, reviewed_at, input_disposition, independent_rationale, final_expected, approved.
- template은 candidate 원문과 분리하고 `official_dataset_update_allowed=false`를 기록한다.

## AC

- GIVEN 후보 3건이 독립 검토 대기 provenance를 가질 때, WHEN packet을 생성하면, THEN 검토 template은 3개 review와 빈 사람 판정 필드를 가진다.
- GIVEN 후보 수·ID·provenance가 계약에 맞지 않을 때, WHEN packet을 생성하면, THEN 오류로 중단하고 산출물을 만들지 않는다.
- GIVEN packet 생성, WHEN 실행하면, THEN provider 호출·공식 Dataset 갱신·유료 평가는 발생하지 않는다.
