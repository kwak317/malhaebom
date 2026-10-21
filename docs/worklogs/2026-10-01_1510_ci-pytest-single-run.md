# Worklog — 백엔드 CI 테스트 중복 실행 제거

- 날짜: 2026-10-01
- 목적: PR Product CI의 경량 의존성 정책과 테스트 범위를 유지하면서 동일 백엔드 테스트를 중복 실행하지 않는다.
- 범위: Product CI workflow 및 이를 검증하는 정적 계약 테스트. 배포·모델 실행 환경과 기존 기록은 변경하지 않는다.

## 작업 전 상태

기존 workflow는 같은 backend 테스트 폴더에 대해 `unittest discover`와 `pytest`를 차례로 실행했다. `backend/requirements-ci.txt`에는 이미 경량 `pytest>=8,<9`가 포함되어 있다.

`backend/tests/test_*.py` 82개 파일을 AST로 확인한 결과 모두 `unittest.TestCase` 클래스를 포함하고, 별도의 최상위 pytest-style 함수로 구성된 테스트 파일은 0개였다. pytest는 `unittest.TestCase`를 수집하므로 두 명령은 기존 테스트를 중복 수행한다.

## 수행 내용

1. Product CI backend job에서 `python -m pytest backend/tests -q`만 실행하도록 변경하고 환경변수 및 경량 CI 의존성은 유지한다.
2. CI 계약 테스트에서 pytest 실행과 unittest 중복 실행의 부재를 검사한다.
3. 다른 팀원의 frontend/배포 구성은 변경하지 않는다.

## 검증

- `python backend/tests/test_pr_policy_workflows.py`: 5개 PASS.
- 독립 탐색: backend test 파일 82개 중 unittest TestCase 파일 82개, 최상위 pytest 함수 파일 0개.
- 기존 PR #149 Product CI가 unittest와 pytest를 모두 통과했다는 이전 기록이 있다.
- 이 변경 뒤 단일 pytest 실행의 GitHub Actions 성공은 이번 PR CI에서 최종 확인한다. 로컬 기본 Python 및 `.venv`에는 pytest가 없어 로컬 전체 suite를 다시 실행하지 않았으며, 별도 설치로 ML runtime을 추가하지 않는다.

## 남은 작업

PR CI 백엔드 테스트의 수집·통과·실행 시간을 확인한다. pytest가 일부 unittest 사례를 놓치거나 환경 특이 실패가 발생하면 병합 전에 보완하고, 실제 시간 절감량은 전후 workflow run 시간으로만 보고한다.
