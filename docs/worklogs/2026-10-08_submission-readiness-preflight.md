# Worklog — 2026-10-08 제출 사전검증 및 증거 인덱스 갱신

- 날짜: 2026-10-08 KST
- 목적: 유료 모델 호출·독립 사람 검토·운영 권한 없이 가능한 검증 결과를 구분해 기록
- 범위: 제출 인덱스의 로컬 확인 및 미완료 근거 갱신. 체크포인트 D10~D12 완료 상태 변경 없음.

## 작업 전 상태
- 기본 작업 트리 `main`은 `origin/main`과 동기화돼 있으나 `docs/worklogs/2026-10-01_stt-b0-c2-drive-handoff.md`에 기존 미커밋 변경이 있음. 이 파일은 변경하지 않음.
- 기존 제출 증거 인덱스의 점검일은 2026-10-06이며, 소개 페이지는 URL 및 소스 상태가 분리되어 있지 않았음.
- 열린 PR은 #213(문서), #214(정적 소개 사이트)이며 둘 다 미승인·미병합 상태.

## 실행 결과

| 검증 | 결과 | 제약 |
| --- | --- | --- |
| `python scripts/check_tracked_artifacts.py` | PASS — 추적 파일 1,084개, ignore 정책 | 이름/경로/크기 검사이며 secret 본문 탐지 아님 |
| C2C Docker profile `proj2-3` status | `api` healthy, `frontend` healthy | 로컬 Compose 상태만 확인. 실제 Cloud Run 배포 아님 |
| `make frontend-test` | ERROR — `sh: 1: vitest: not found` | npm 의존성 미설치로 테스트 자체 미수행. 코드 실패로 간주하지 않음 |
| `python site/scripts/check_site.py` | PASS — 18/7 IDs, 31/30 links/assets | 별도 `proj2-3-site` 로컬 트리 기준. GitHub Pages 공개 확인 아님 |
| `git diff --check` | PASS | 추적된 diff 공백 검사만 수행 |

## PR 및 체크리스트 상태
- #213: OPEN, 리뷰 승인 없음, 4개 check 실패. D7 종료 기록은 `main`에 미반영.
- #214: OPEN, 리뷰 승인 없음, 5개 check 실패. 로컬 정적 소개 사이트 소스 존재와 공개 URL 동작은 별도.
- Actions 로그 원인을 직접 확인하지 못했으므로 CI 실패 사유는 미확정이다.
- `docs/SUBMISSION_EVIDENCE.md`에 위 결과를 사전점검으로 추가하며 D11 사람 검토·전후 측정, D10 production trace/rollback, D12 최종 제출 및 코드 동결의 미완료 상태는 유지한다.

## 후속
1. CI 실행 할당량/워크플로 오류를 분리 확인하고 #213·#214를 팀원 리뷰 후 병합.
2. `frontend` 의존성이 복원된 개발 환경에서 단위 테스트를 재실행.
3. 최종 제출 전 공개 URL, 운영 revision, Secret Scan, E2E 및 Langfuse 캡처를 같은 실행 기준으로 증거화.
