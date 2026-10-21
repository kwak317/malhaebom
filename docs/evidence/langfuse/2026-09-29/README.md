# Langfuse UI evidence — 2026-09-29

이 디렉터리는 D6 Langfuse 검증의 보조 UI 증거를 보관하기 위한 위치다. canonical 근거는 Worklog의 trace ID와 구조화 metadata이며, 스크린샷은 사람이 빠르게 상태를 확인하기 위한 보조 자료다.

## 현재 보관 상태

이번 검증에서 확보한 원본 UI 캡처에는 사용자 ID, session ID, 조직/프로젝트명이 함께 표시되어 있어 저장소에는 그대로 커밋하지 않는다. 현재 canonical 증거는 Worklog에 기록한 trace ID와 구조화 metadata다.

발표·리뷰용 UI 증거가 필요해 식별 정보를 제거한 캡처를 추가할 경우 다음 파일명을 사용한다.

## 권장 파일명

- `retry-attempt-1.png`
  - trace `edeb73e5d1424c9fa877c00509ef9473`
  - `transport_attempt=1`
  - `outcome=network_error`
  - `will_retry=true`
  - `retry_reason=network_error`
- `retry-attempt-2.png`
  - 같은 trace의 두 번째 provider observation
  - `transport_attempt=2`
  - `outcome=network_error`
  - `will_retry=false`
- `success-trace.png`
  - trace `7f67f14ceb9040868bad4249903c79a8`
  - `coaching.provider`, `coaching.output_validation`, `coaching.analyze`
  - model / token / cost 표시

## 캡처 정리 규칙

전체 브라우저 화면을 그대로 커밋하지 않는다. 필요한 trace tree와 metadata 영역만 crop하고 다음 값은 가리거나 제외한다.

- 사용자 ID / session ID
- 조직·프로젝트명 등 불필요한 계정 식별 정보
- access token, secret key, 원문 Prompt
- 사용자 답변·전사 원문·공고 원문

Langfuse public key는 secret은 아니지만 검증에 필요하지 않으므로 가능하면 crop 영역에서 제외한다.

자세한 실행 기록은 `../../../worklogs/2026-09-29_1430_langfuse-authenticated-e2e.md`를 참조한다.
