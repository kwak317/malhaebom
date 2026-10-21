# Worklog — PR #70 canonical devset 고정

- 일시: 2026-09-28
- 작업자/에이전트: Codex
- 관련 PR: #70

## 1. 목적

임의 SHA override로 다른 ZIP·대본을 동일 frozen devset으로 생성하는 경로를 막는다.

## 2. 작업 전 상태

기본 SHA는 고정되어 있었으나 CLI의 두 expected SHA 옵션으로 다른 자료를 통과시킬 수 있었다.

## 3. 수행 내용

CLI override 옵션을 제거하고 canonical ZIP·대본 SHA를 강제했다. metadata의 기존 override 필드는 항상 false로 유지했다.

## 주요 판단과 이유

별도 데이터셋 버전은 별도 실험 경로로 관리해야 하므로 이 도구는 canonical devset만 생성한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/scripts/prepare_stt_real_user_devset.py` | canonical SHA 강제 |
| `backend/tests/test_stt_real_user_devset.py` | SHA override 거부 회귀 |

## 5. 검증

- `python -m unittest backend.tests.test_stt_real_user_devset -v`: 8개 통과.
- `git diff --check`: 통과.
- `python -m unittest backend.tests.test_stt_real_user_devset backend.tests.test_stt_real_user_eval_utils -v`: #70 브랜치에는 후속 #81의 eval_utils 테스트가 없어 import 오류. devset 테스트 단독 재실행은 8개 통과.

## 6. 발견한 문제 / 남은 리스크

- 없음.

## 미확인 사항

- 실제 원본 음성 ZIP을 사용한 devset 생성은 하지 않았다.

## 7. 다음 작업

- #71의 devset provenance를 연결한다.
