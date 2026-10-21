# Worklog — 2026-10-08 D11 독립 사람 검토 패킷 인계

- 일시: 2026-10-08 KST
- 목적: 기존 D11 후보 3건의 사람 검토를 실제로 진행할 수 있는 로컬 전달물 생성 및 체크리스트 정합성 기록
- 범위: provider 호출, 모델·Prompt·Skill 변경, 사람이 아닌 독립 검토, 공식 Dataset 승격은 제외

## 작업 전 상태

- `main`은 `origin/main`과 동일하나 다른 작업의 미커밋 수정(`docs/SUBMISSION_EVIDENCE.md`, `docs/worklogs/2026-10-01_stt-b0-c2-drive-handoff.md`, `docs/worklogs/2026-10-08_submission-readiness-preflight.md`)이 있어 보존함.
- D11 신규 인젝션 후보는 3건 모두 user-approved 제안 판정이며 `independent_human_authored_input_pending` 상태.
- 기존 패킷 생성기 `evals/build_d11_injection_human_review.py` 및 회귀 테스트 2개가 이미 존재.
- 10/2 Gemini v5 자동 불일치 7건의 원본 비교 파일은 `local-results/gemini-v5-4096-live-30/comparison.json` 표준 위치에서 발견되지 않음.

## 수행 내용

1. D11 패킷 생성기에 기본 출력 경로(`local-results/d11-injection-review-20261008`)를 추가했다. 별도 `--output-dir` 지원 및 기존 경로 덮어쓰기 방지는 유지했다.
2. 기존 생성기를 실행해 `REVIEW.md`와 사람 판정 필드가 빈 `human-review.template.json`을 실제 생성했다.
3. [D11 검토 인계 문서](../evidence/d11-human-review-handoff-2026-10-08.md)에 후보 3건·판정 유형·독립 검토자 조건과 공식화 기준, 별도 v5 자동 불일치 7건 원본 누락을 분리 기록했다.
4. [체크포인트 문서](../project2-checkpoint-work-cards.md) D11 기존 부분완료 항목에 10/8 패킷 생성 근거만 추가했다. 실제 사람 판정 완료 및 before/after의 완료 여부는 바꾸지 않았다.
5. [D11 Spec](../specs/d11-human-review-preflight.md)에 기본 경로와 덮어쓰기 방지를 기록했다.

## 검증

- `backend/tests/test_build_d11_injection_human_review.py` 직접 실행: 2 tests OK.
- 패킷 실행: exit 0, `D11 human review packet written: local-results/d11-injection-review-20261008`.
- `Provider calls: 0; official dataset update: NOT AUTHORIZED`.
- 별도 Gemini v5 7건 기존 테스트를 파일 직접 실행할 때 `ModuleNotFoundError: No module named 'evals'`가 발생했다. 이는 그 실행 방식의 모듈 경로 문제이고 코드 자체의 테스트 실패로 결론 내리지 않는다. `comparison.json` 입력이 없어 해당 패킷을 재생성하지 않았다.

## 남은 문제와 후속

1. 기존 후보 승인에 참여하지 않은 독립 사람이 입력·정답·근거를 검토하거나, 사람이 실질적으로 입력을 새로 작성·수정할 것.
2. 검토자·시각·독립 근거·최종 정답 기록 뒤 팀에서 공식 Dataset 승격을 따로 승인할 것.
3. 보존된 10/2 Gemini v5 원본 `comparison.json`을 찾거나 팀으로부터 인계받고 기존 7건 양식 생성 도구로 검토할 것.
4. 10/6 배포 이미지 90출력과 10/2 v5 7건을 다른 실험으로 구분해 human semantic/critical 평가를 실시할 것.
5. 승인된 동일 조건 및 유료 호출 예산으로만 D11 방어 before/after를 실행할 것.

로컬 평가 출력은 git-ignored `local-results/`에 보관한다. 이번에는 커밋·푸시·PR 생성·유료 provider 호출을 수행하지 않았다.
