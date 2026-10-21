# 2026-09-30 — 제품 테스트 CI 추가

## 목적

강사 피드백 보완 체크의 서비스 완성도 항목을 위해 PR마다 backend 회귀, frontend unit test, frontend production build를 자동 실행하는 GitHub Actions CI를 추가한다.

## 작업 전 상태

- 기존 GitHub Actions는 PR review-size 정책과 secret scan을 중심으로 동작했다.
- backend 전체 테스트, frontend `npm test`, frontend production build는 Worklog에서 수동 실행 기록은 있었지만 모든 PR의 자동 제품 CI로 고정되어 있지 않았다.
- 공식 D10 외부 배포 검증과 이번 제품 테스트 CI는 별도 범위로 유지한다.

## 수행한 작업

- `.github/workflows/product-ci.yml`을 추가했다.
- PR의 opened / synchronize / reopened 이벤트에서 Product CI를 실행한다.
- backend job은 Python 3.12와 CI 전용 `backend/requirements-ci.txt`를 사용해 전체 `unittest` discovery를 실행한다.
- CI 전용 requirements에서는 `faster-whisper`, `silero-vad`, PyTorch/torchaudio 같은 모델 runtime 의존성을 제외한다. 해당 경계의 단위 테스트는 fake/model loader 주입으로 검증한다.
- frontend job은 Node.js 22.14.0에서 `npm ci` 후 `npm test`와 production build를 순서대로 실행한다.
- dependency cache와 concurrency cancel을 적용해 반복 PR 실행 비용을 줄인다.
- `backend/tests/test_pr_policy_workflows.py`에 Product CI의 핵심 계약을 검사하는 정적 회귀 테스트를 추가했다.
- PR #137의 첫 실제 Product CI 실행에서 backend와 frontend job이 모두 성공한 뒤 강사 피드백 체크리스트를 완료 처리했다.

## 주요 판단과 이유

- backend는 일부 선택 테스트보다 현재 저장소 전체 `backend/tests`를 실행해 PR마다 제품 회귀를 넓게 잡되, 테스트에 불필요한 음성/모델 runtime 설치 비용은 분리한다.
- STT/TTS 신규 학습이나 GPU 검증은 제품 CI 범위에 넣지 않는다. 해당 실험은 별도 트랙이다.
- frontend test와 build는 같은 job에서 실행하되 단계 이름을 분리해 어느 단계가 실패했는지 GitHub Actions에서 바로 확인할 수 있게 한다.
- CI는 repository secret 없이 실행 가능해야 하며 실제 provider/배포 검증은 D10 및 별도 E2E에서 수행한다.

## 변경 파일

- `.github/workflows/product-ci.yml`
- `backend/requirements-ci.txt`
- `backend/tests/test_pr_policy_workflows.py`
- `docs/project2-checkpoint-work-cards.md`
- `docs/worklogs/README.md`
- `docs/worklogs/2026-09-30_1617_product-test-ci.md`

## 검증

- 경량 CI requirements 계약 추가 후 `backend/tests/test_pr_policy_workflows.py`: 5 tests, OK.
- 로컬 C2C 실행에서 `make frontend-test`와 `make frontend-build`를 시도했으나 현재 checkout에 frontend 의존성이 설치되어 있지 않아 각각 `vitest: not found`, `tsc: not found`로 시작 전 종료했다. 애플리케이션 테스트 실패로 판정하지 않는다.
- PR #137 GitHub Actions 실측: `Backend tests` SUCCESS.
- PR #137 GitHub Actions 실측: `Frontend tests and build` SUCCESS. clean runner에서 `npm ci` 후 frontend test와 production build가 모두 통과했다.
- 따라서 경량 CI requirements로도 backend 전체 suite가 통과하며 Product CI 완료 게이트를 충족했다.

## 발견한 문제

- 로컬 checkout의 frontend `node_modules`가 없어 기존 Makefile test/build target만으로는 바로 재현되지 않았다.
- 새 Product CI를 branch protection의 required check로 강제하는 설정 여부는 저장소 코드만으로 확정하지 않는다.

## 미확인 사항

- 경량 requirements 적용 전후의 정확한 job duration 비교는 아직 별도 수치로 기록하지 않았다.
- Product CI check를 GitHub ruleset/branch protection의 필수 상태 검사로 지정할지는 별도 운영 결정이 필요하다.

## 다음 작업

1. Product CI check를 ruleset/branch protection의 필수 상태 검사로 지정할지 운영 기준을 정한다.
2. CI 비용이나 실행 시간이 과도하면 테스트 범위를 임의로 줄이지 말고 캐시/병렬화부터 조정한다.
