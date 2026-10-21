# Worklog — 전체 백엔드 재검증

- 일시: 2026-10-09 KST
- 관련 PR: #234 (운영 동기화 stack 최종 후보)
- 사용자 지시: 전체 backend 테스트와 실제 인증·LLM·DB 흐름 미확인 사항 보완

## 목적 및 수행

종료 코드 137로 중단된 전체 suite를 GitHub CI용 가벼운 의존성 환경에서 재검증했다. 운영 설정·배포·모델·DB 스키마는 변경하지 않았다. 코드 수정 없이 전체 814 tests가 31.39초에 정상 종료(exit 0)했다. 이전 강제 종료의 정확한 원인은 확정하지 않았다.

## 환경과 재현

Python 3.12-slim + git, `backend/requirements-ci.txt`, STT_WARMUP_ENABLED=false, PYTHONPATH=.:backend:backend/tests, 컨테이너 메모리 3 GB, 원본 candidate read-only mount.

`python -m pytest backend/tests -q -p no:cacheprovider`

[세부 결과](../evidence/production-sync-20261009/full-backend-result.json)를 따른다. 준비·코칭의 가짜 모델/저장소 경계 검증을 실제 provider/DB E2E와 혼동하지 않는다.

## 실제 운영 흐름 검증 진행 상태

잠금 해제 후 별도 Chrome 탭의 기존 로그인 세션으로 preparation 채팅을 실행했다. 익명 요청 401, 인증 POST/confirmed GET 200, 실제 Haiku 응답, 팀 경험의 개인 역할 질문, 역할 답변 후 별도 저장 동의, 참고정보 2건의 DB 저장·재조회·자료실 표시 및 항목 펼침을 확인했다. 운영 DB에는 새 대화의 합성 테스트 자료만 추가했고 기존 자료·배포 설정·Langfuse·main은 변경하지 않았다.

총 9개 체크 중 7개 통과, 2개 실패다. 저장 질문 직후 `네 맞습니다`와 `네, 연습 참고정보로 반영해줘`는 동의로 인정되지 않았다. 안내된 `반영해줘` 및 별도 저장 질문 뒤 `네`는 저장됐다. 실패 응답은 HTTP 200이라도 기능 성공으로 세지 않았고 실패 턴은 DB history에 남지 않았다. 운영과 소스의 일치를 유지하는 이번 PR에서 정책을 몰래 변경하지 않고 결함을 기록했다.

[실제 검증 결과](../evidence/production-sync-20261009/authenticated-chat-e2e-result.json)를 따른다. Cloud Run 요청 trace와 Langfuse generation은 동일 ID로 조회했으며 브라우저는 정확한 테스트 문구·대화 UUID·시간으로 대응했다. 브라우저 응답 헤더를 직접 캡처한 trace 연결은 아니다. DB 확인은 동일 대화 UUID의 read-only service-role 조회로 보완했으며 사용자 JWT 인증 검증을 대신하지 않는다.

실제 provider observation은 `anthropic/claude-haiku-5.5`, outcome success이며 자유채팅 span에 15,584 input / 624 output tokens가 기록됐다. provider의 coaching managed Prompt 태그는 관측 공통 설정이며 자유채팅 입력 본문이 해당 managed 코칭 Prompt였다는 증거로 사용하지 않는다.

브라우저 제어 도구의 한국어 입력과 화면 캡처가 불안정해 입력 문구를 접근성 상태로 확인한 뒤 전송했다. 마지막 화면 캡처는 접근성 상태보다 과거 화면을 보여 최신 자료실 증거로 사용하지 않았다. 자료실 2건과 저장 내용은 갱신된 접근성 트리·confirmed GET·DB로 검증했다. 신규 OAuth 로그인, 실제 마이크/STT/코칭/비교 전체 제품 흐름 및 150건 품질 평가는 이번 검증 범위에 포함하지 않는다.
