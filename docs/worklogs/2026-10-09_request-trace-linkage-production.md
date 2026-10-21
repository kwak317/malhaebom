# Worklog — 운영 HTTP 요청·Langfuse trace 직접 연결

- 일시: 2026-10-09, 운영 브라우저 검증 10:37 KST
- 작업자: Codex, 사용자 승인으로 배포·증거 수집·PR 생성; merge 제외

## 1. 목적

사용자가 보낸 HTTP 요청을 응답 헤더에서 Langfuse trace와 운영 revision까지 직접 연결한다.

## 2. 작업 전 상태

직전 운영 revision은 `malhaebom-mk2-reference-finish-1009-verified`였다. 준비 대화 내부 trace와 HTTP 요청의 연결 및 모델 호출 전 오류의 관측을 보완해야 했다.

## 3. 수행 내용 및 주요 판단

- 서버가 각 HTTP 요청에 ID를 부여하고 서비스·모델 관측에 같은 context를 전달했다.
- 응답의 X-Trace-Id·X-Request-Id와 CORS expose_headers를 맞추고, http.request에 상태·경로·지연만 기록했다.
- 요청 본문·Authorization·query는 새 HTTP 관측에 기록하지 않는다. 예외의 응답은 표준 500 본문을 유지한다.
- 직전 운영 이미지를 기준으로 변경 파일만 overlay했다. 후보 무트래픽 검증 뒤 100%로 전환했다.
- GitHub main `fd9a6b9`에는 해당 관측 변경만 이식했다. 기존 전문가 검토 PR #219와 운영의 다른 기능 변경은 포함하지 않는다.

## 4. 변경 파일

- backend/app/main.py, routers/preparation_conversation.py, services/coaching_observability.py, services/request_trace.py
- backend/tests/test_request_trace_linkage.py, docs/specs/request-trace-linkage.md
- 증거 문서·스크린샷·evals/results JSON, CURRENT_STATE·체크포인트·Worklog 인덱스

## 5. 검증

- `python -m unittest`로 새 linkage 테스트 12개, 운영 overlay 집중 38개·preparation 133개·자유 채팅 30개, GitHub main 집중 33개 통과. 중복을 포함한 별도 suite이므로 합산하지 않는다.
- 첫 실행의 app import 경로 오류를 PYTHONPATH로 수정하고 전체 대상 suite를 다시 실행했다.
- Cloud Build `a8b5e406-e882-46b9-9973-3b0f047ced54` 성공. 운영 revision은 `malhaebom-mk2-request-trace-linkage-1009`.
- 실제 사이트 채팅 200과 브라우저 스키마 오류 422의 헤더·Langfuse·Cloud Run ID가 일치했다. [증거와 재현 절차](../evidence/request-trace-linkage-2026-10-09.md).
- 성공에는 실제 모델 호출 1개, 입력 오류에는 0개. 임시 인증 세션·사용자·로컬 인증 파일 정리 완료.

## 6. 발견한 문제 / 미확인 사항

Langfuse 전송 장애 시 헤더만으로 기록 성공을 보장하지 않는다. OAuth 로그인 화면·마이크/STT·사람 품질 평가는 미검증이며 기존 유보 상태를 유지한다.

## 7. 다음 작업

PR은 공개 리뷰용으로 올리고 merge하지 않는다. 사람 평가 등록 시 평가 대상 trace ID를 직접 지정해 이번 증거와 구분한다.
