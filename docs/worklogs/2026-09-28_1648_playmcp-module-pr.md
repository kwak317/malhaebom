# Worklog — PlayMCP 연결 모듈 PR

- 요청: 지금까지 작업한 내용을 PR로 올리고 merge하지 않기.
- 최신 base: `origin/main` `5c495d5`. 실행 중인 원래 checkout과 서비스는 수정하지 않았다.

## 목적과 범위

PlayMCP 사람인 검색 모듈의 MCP 호출·토큰 갱신·URL 허용 검증을 독립적으로 검토한다. 추천 공급자 활성화는 후속 PR로 분리해 검토 대상 400줄 한도를 지킨다.

## 변경 파일

- `backend/app/services/playmcp_job_search.py`: 기존 MCP SDK 직접 호출, 고정 공개 검색어, 허용 URL 정규화, 제한된 401 재시도, 단일 프로세스 token 갱신·0600 원자적 저장.
- `backend/tests/test_playmcp_job_search.py`: URL·빈 응답·토큰 유효/만료/누락·갱신 거부의 6개 테스트. 서비스 연동 테스트는 후속 PR에서 추가한다.
- `docs/specs/playmcp-job-search.md`, `docs/CURRENT_STATE.md`, 본 Worklog.

## 검증과 제한

- 새 인증·URL 테스트는 외부 네트워크와 실제 인증값 없이 검증한다.
- 실제 로컬 연결·검색은 기존 작업에서 성공했으며 전체 호출·속도·사용자 E2E 한계는 후속 연동 Worklog에 함께 기록한다.
- 개인 인증 파일과 로컬 `.env`, 이미지·실행 산출물은 PR에 포함하지 않는다. 다중 worker 갱신 공유는 지원하지 않는다.
- 이 PR만으로 앱 공급자는 바뀌지 않는다. 기본 웹검색을 유지하고 후속 연동 PR에서 선택한다.
- 최신 main의 별도 checkout·호환 검증 이미지에서 신규 모듈 테스트 6개가 통과했다. 기존 main baseline 471개도 같은 검증 이미지에서 통과했다.

## 2026-09-29 PR #97 권한 리뷰 수정

- 기존 인증 파일을 연 뒤 같은 descriptor의 `fstat` mode가 0600인지 확인하고 JSON을 읽는다. 불일치는 읽기·refresh 전에 거부하며 파일 권한을 임의 변경하지 않는다.
- 0644·0640·0660의 정상 조회/강제 갱신 거부, JSON 읽기·갱신 요청 없음, 권한 보존·secret 미노출 회귀 테스트를 추가했다. 수정 전 세 mode 모두 거부되지 않는 실패를 재현했고, 수정 후 기존 0600 조회/갱신을 포함해 7개 테스트가 통과했다.
- 네트워크 차단 검증 컨테이너에서 실제 인증값 없이 테스트했다. 변경 파일은 모듈·테스트·Spec·CURRENT_STATE·본 Worklog뿐이다. 실행 중인 서비스와 개인 인증 파일은 수정하지 않았다. 실제 PlayMCP 호출·mount E2E는 재실행하지 않았다.
- `git diff --check`, gitleaks 파일 검사와 PR 정책 검사가 통과했다. review core는 379줄이며 Worklog는 증빙 예외로 분류된다.
