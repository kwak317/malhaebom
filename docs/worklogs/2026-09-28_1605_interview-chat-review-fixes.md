# Worklog — PR #90 코칭 호환성·요청 재사용 수정

- 일시: 2026-09-28 16:05 KST
- 작업자: Codex
- 관련 PR: [#90](https://github.com/aihuman-7th/proj2-3/pull/90)

## 1. 목적
리뷰의 P1 호환성 확인과 P2 성공 요청 ID 재사용 보장을 충족한다.

## 2. 작업 전 상태
run 조회는 Skill 버전만 읽고 비교했다. criteria_version은 run에 저장되지 않았다. 마지막 요청만 기억해 A→B→A가 새 턴이 되거나 같은 ID의 변경 입력을 허용했다. 추가한 회귀 테스트에서 이 문제들을 재현했다.

## 3. 수행 내용
두 run의 model/Prompt/Skill/실제 criteria 버전 존재·일치와 현재 질문 기준을 확인한다. 새 코칭 저장은 서버 question의 criteria_version을 기록한다. 새 nullable 컬럼은 과거 버전을 추정해 채우지 않는다. 요청 ID별 action/message/성공 응답을 대화 수명 동안 보관하고, 실패 생성은 캐시에 넣지 않는다. 재사용 전에 기존 소유권·만료·기록 변경 검사를 유지한다.

## 주요 판단과 이유
같은 기준 ID·Skill 문자열만으로 실제 기준이 같다고 증명할 수 없어 저장 메타데이터를 추가했다. 기존 사용자 DB와 실행 컨테이너는 수정하지 않고 별도 worktree에서 작업했다. #92의 API 테스트 데이터에는 새 필수 메타데이터를 추가해 두 PR의 통합 검증에 사용한다.

## 4. 변경 파일
- `backend/app/services/interview_chat.py`: 호환성·성공 요청 재사용
- `backend/app/services/supabase_coaching_runs.py`: 서버 기준 버전 저장
- `backend/tests/test_interview_chat_service.py`, `test_supabase_coaching_persistence.py`: 회귀 검증
- `supabase/migrations/20260928065116_coaching_run_criteria_version.sql`: nullable 컬럼·공백 값 거부
- `docs/specs/post-comparison-interview-chat.md`, `docs/CURRENT_STATE.md`, 이 Worklog

## 5. 검증
- 서비스·저장 계약 테스트 11개 통과. model/Prompt/Skill/criteria 불일치, 양쪽 run의 필드 누락·빈 값·null, 구 criteria 일치도 차단, A→B→A, ID의 메시지/action 변경, 종료 후 재전송, 실패 후 같은 ID 재시도를 포함한다.
- `python -m unittest discover -s backend/tests`: 455개 통과. 최초 전체 실행은 테스트 venv의 Langfuse 의존성 누락으로 2개 오류였으며 선언된 의존성 설치 후 통과했다.
- 사용자 JWT를 유지한 MockTransport 조회에서 새 필드 선택과 모델 호출 전 차단을 검증했다.
- #92의 API 코드·갱신한 테스트 데이터와 #90 수정안을 별도 복사본에서 함께 적용한 백엔드 전체 468개가 통과했다. HTTP chat 정상/권한/만료/삭제/재시도·계약 실패·종료·기록 변경 경로를 포함한다.
- 기존 `postgres:18` 이미지의 네트워크 없는 임시 컨테이너에서 migration 실행과 과거 NULL 유지·실제 버전 저장·공백 값 거부를 검증했다. 테스트 컨테이너는 종료 후 자동 제거했다.

## 6. 발견한 문제 / 남은 리스크
단일 프로세스 메모리·재시작/다중 worker 복원 미지원은 기존 제약이다. 요청 응답 캐시는 대화 만료까지 유지된다. 과거 NULL 버전 기록은 같은 기준으로 재분석해야 대화를 시작할 수 있다.

## 미확인 사항
운영·공유·기존 로컬 DB에는 migration을 적용하지 않았다. 서비스 배포 전 새 migration을 적용해야 한다. 실제 사용자 로그인·DB·외부 LLM E2E는 이번 검증이 아니다.

## 7. 다음 작업
선행 PR 순서대로 검토하고 새 migration 적용을 검증한 뒤 작성자가 통합한다. 이번 요청에서는 머지하지 않는다.
