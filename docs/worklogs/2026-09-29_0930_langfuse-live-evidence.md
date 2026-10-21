# Worklog — 실제 호출 Langfuse 캡처

- 일시: 2026-09-29 09:25~09:31 KST
- 목적: 입력·출력·지연이 저장된 실제 trace 화면 확보.

## 작업 전 상태

현재 `proj2-3-complete-flow-api-1`의 Langfuse 2.60.10 sink는 metadata만 기록한다. 기존 실제 호출 trace에는 input/output과 endTime/latency가 비어 있었다. 다른 smoke 기록은 실제 provider 호출 증거로 사용하지 않았다.

## 수행 및 검증

- 현재 컨테이너의 실제 `google/gemini-3.5-flash-lite` provider와 서버 코칭 검증기를 호출했다. 기존 합성 fixture와 테스트 인증, 저장소 없는 API TestClient를 사용했다.
- `/api/agent` HTTP 200, `status=ok`, 실제 completion ID, 모델 호출 1회, provider 지연 3540.798ms를 확인했다.
- 검증 스크립트에서 실제 입력·출력과 start/end를 기록했다. 구형 수집 지연으로 같은 호출 원본 기록을 공식 OTLP HTTP/JSON endpoint로 재전송했다. 새 모델 응답이나 임의 지연 값을 만들지 않았다.
- Observations API v2로 원격 trace를 재조회했다. 입력·출력의 원본 일치 및 timestamp 차이와 latency `3.676s`의 일치를 확인했다.
- Safari에서 해당 trace의 입력·판정·지연 `3.68s`가 동시에 보이는 화면을 캡처했다. JPEG 3024×1898을 확인했다.
- 실제 호출 이미지와 현재 checkout의 provider/서버 검증기 SHA-256이 일치했다.

## 증거 파일

프로젝트 상위 `output/langfuse-trace-20260929/`:

- `trace-input-output-latency.jpg`: Safari 원본 캡처.
- `live-result.json`: 실제 호출 응답·completion ID·소스 해시.
- `verified-evidence.json`: 원격 IO·지연 재조회 및 일치 결과.
- `verify_synthetic_live_trace.py`, `export_recorded_trace_otel.py`: 검증 호출 및 실제 기록 재전송 코드. 인증값은 환경변수에서만 읽는다.

원격 확인 trace: `21054d8ea9cd5bfc92569370bc6c3921`, observation: `aeefaf50b3cf0758`. 원래 SDK 기록 trace: `24d83d32ff2a414fafc72f475327c5c1`.

## 범위와 남은 사항

검증 전용 계측의 실제 모델 호출 증거다. 운영 tracing 코드·컨테이너 설정·사용자 DB·Prompt/Dataset은 수정하지 않았다. 로그인 사용자 브라우저 E2E, 모든 운영 호출의 IO 자동 기록 완료를 증명하지 않는다. 운영 sink의 IO·종료시각 연결은 별도 보완이 필요하다. commit/push/PR/배포는 수행하지 않았다.

OTLP 형식과 수집 방식은 [Langfuse 공식 문서](https://langfuse.com/integrations/native/opentelemetry)를 확인했다.

## 후속 문서 정리

- 사용자 요청으로 상위 `말해봄_D6_실제LLM_검증재시도_20260929.md`에 호출·검증·보정 코드, 실패 응답 JSON, 파싱 실패 정책, 지시/데이터 출처 구분, 위 캡처와 확인 범위를 통합했다. 에러 로깅은 제외했다.
- 기존 문서를 `output/doc-backups/말해봄_D6_실제LLM_검증재시도_20260929.before-consolidation.md`로 백업하고 변경 diff를 확인했다.
- Markdown fence 짝, Python 발췌 문법(독립 실행 가능한 블록), 실패 JSON, 로컬 링크·이미지 존재, 기록된 측정값 대조를 통과했다. API/운영 설정은 변경하지 않았다.
