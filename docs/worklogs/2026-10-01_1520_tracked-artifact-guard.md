# Worklog — 추적 파일 및 제외 규칙 점검 자동화

- 날짜: 2026-10-01
- 목적: 배포/학습 코드와 비밀 내용을 건드리지 않고 저장소에 민감 파일명·대형 생성 자산이 새로 추적되는 실수를 줄인다.

## 작업 전 상태

- `.gitignore`에는 `.env` 파일, 모델 가중치, 음성 파일, `local-results/` 등이 이미 제외 대상으로 등록되어 있다.
- 기존 프로젝트 지침은 별도 secret-scanning workflow를 명시하고 있다.
- 실제 추적 대상과 예상 제외 규칙이 일치하는지 반복 검사할 작은 회귀 테스트는 별도로 없었다.

## 수행 내용

1. 파일 내용·비밀값은 읽지 않고 `git ls-files`로 파일명, 5 MiB 초과 여부 및 `git check-ignore --no-index`로 제외 규칙만 확인한다.
2. 개발·평가 출력, 민감한 설정 및 키 이름, 모델·음성 확장자 신규 추적을 차단하는 `scripts/check_tracked_artifacts.py`를 추가한다.
3. `.env.example` 예외와 금지 패턴, 현재 저장소 검사 결과를 검증하는 unittest 기반 3개 회귀 테스트를 추가한다.
4. 검증 범위와 한계를 `docs/evidence/2026-10-01-tracked-artifact-audit.md`에 명시한다.

## 검증

- `python scripts/check_tracked_artifacts.py`: PASS (현재 추적 파일 835개, ignore sentinel 검증 완료)
- `python backend/tests/test_tracked_artifacts.py`: 3 tests PASS.
- 새로운 backend 테스트 파일은 Product CI의 기존 backend suite가 자동 수집한다.

## 남은 작업과 제한

- 콘텐츠 수준의 secret 스캔을 새로 구현하거나 기존 gitleaks를 대체하지 않는다.
- 이 검사로 과거 Git history의 유출 여부, 운영 인프라의 secret 배치 또는 실제 개인정보 안전성을 증명할 수 없다.
- 프런트엔드/백엔드 배포 설정, 과거 Worklog 및 팀원의 현재 작업 파일은 변경하지 않는다.
