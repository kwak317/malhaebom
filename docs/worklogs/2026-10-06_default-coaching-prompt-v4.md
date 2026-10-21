# Worklog — 코칭 기본 Prompt를 배포 v4로 복원

- 일시: 2026-10-06
- 작업자/에이전트: Codex
- 관련 요구사항/결정: 사용자 요청 “깃허브 기본값을 배포에서 쓰고있는 v4버전으로 바꿔줘”

## 1. 목적
환경변수 미설정·공백에서 선택하는 기본값과 v4 본문을 배포 기준에 맞춘다.

## 2. 작업 전 상태
- 최신 main `b9f7246a92160b8492ad4a7a25f69c049b24f6e9`에서 별도 worktree를 만들었다. 기존 checkout 변경과 어제 만든 후보를 사용하지 않았다.
- Cloud Run 조회에서 `malhaebom-mk2-resume-1004-1438`에 트래픽 100%, 이미지 digest `sha256:82b0cae6f08df6242f827f2b24791759e318c4a73b7cf6c0066e13caaa7bab75`를 확인했다. Prompt 버전 및 관리형 Prompt 이름 환경변수가 없어서 이미지의 v4 기본값을 사용한다.
- GitHub는 v5 기본값이며 v4 본문에 배포 원본보다 intent 설명 4줄이 추가되어 있었다.
- 변경 전 Prompt·분리 테스트 24건 통과.

## 3. 수행 내용
기본 상수·설정 예시를 v4로 변경하고 불변 배포 archive의 v4 본문을 복원했다. v5 판정 분리 테스트는 v5를 명시 선택하게 하고 기본·복귀 테스트는 v4를 검증한다.

## 주요 판단과 이유
사용자 요청에 맞춰 배포 Prompt 원본을 사용했다. 현재 GitHub Skill은 보존하므로 전체 Prompt+Skill 조합이 운영과 동일하다고 주장하지 않는다. 도메인 규칙이 Skill에만 존재하는 구조는 v5 명시 선택에 한정된다.

## 4. 변경 파일
- `backend/app/services/coaching_prompt.py`, `.env.example`: 기본값 v4.
- `prompts/coaching-user-supplied-v4-verification.md`: 배포 본문 복원.
- `backend/tests/test_coaching_prompt.py`, `backend/tests/test_prompt_skill_separation.py`: 기본 v4·명시적 v5·관리형 복귀 회귀 검사.
- `docs/specs/default-coaching-prompt-v4.md`, `docs/specs/coaching-domain-rules-in-skill.md`: 기본값과 명시적 v5 범위 정합성.
- `docs/CURRENT_STATE.md`, 이 Worklog 및 목록: 변경·검증 기록.

## 5. 검증
```text
PYTHONPATH=backend/tests:backend:. <기존 test-venv>/bin/python -m unittest backend.tests.test_coaching_prompt backend.tests.test_prompt_skill_separation backend.tests.test_coaching_runtime
Ran 50 tests — OK
```
첫 변경 후 v5 전용 규칙을 기본값에 기대한 테스트 1건이 실패했다. 해당 테스트를 명시적 v5 선택으로 수정한 뒤 전체 50건이 통과했다.

v4 템플릿 SHA256은 불변 baseline manifest와 일치한다: `2d8cf1d83254c65b638d55ec69d10229a7d3e680f274c6ee8e6d02cf65dd0fb1`.

## 6. 발견한 문제 / 남은 리스크
명시적 `.env`나 유효한 Langfuse 관리형 Prompt 선택은 기본값보다 우선한다. 기존 배포나 실행 컨테이너는 PR만으로 바뀌지 않는다.

## 미확인 사항
실제 LLM 평가·사용자 E2E·배포를 수행하지 않았다. 테스트 통과는 모델 품질 개선 증거가 아니다.

## 7. 다음 작업
팀원 리뷰 후 병합 여부를 결정한다. 운영 배포는 이번 범위에 포함하지 않는다.

## 2026-10-06 PR #168 병합 요청 후 충돌 해결

- 사용자에게 PR #168 병합 승인을 받았다. 팀원 `nanocode00`의 approve와 기존 CI 4개 성공을 확인했다.
- 최신 main `1bf7211`을 병합하며 `CURRENT_STATE.md` 상단의 새 절 삽입 충돌 1건을 해결했다. v4 복원 기록과 PR #166 I/D 사례 9·10 기록을 모두 최상위 제목 아래에 보존했다.
- main의 Skill·Spec·Worklog 변경은 그대로 통합하며 PR 자체의 코드·설정·v4 본문은 수정하지 않았다.
- 충돌 해결 후 관련 Prompt·분리·runtime 테스트 50건, 제목·기존 main 기록 보존 검사 및 diff whitespace 검사를 다시 수행한다. 최신 head CI 결과 확인 후 병합한다. 운영 배포는 제외한다.
