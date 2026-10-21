# HTTP 요청과 Langfuse trace 직접 연결

## Why

운영 요청을 시각만으로 trace와 연결하면 같은 시간의 다른 요청을 구분하기 어렵다.

## Goal

코칭·준비/자유채팅·비교 후 면접 대화의 응답 헤더와 Langfuse trace ID가 정확히 일치한다. Prompt·모델·사용자 UI·평가 정답 변경은 제외한다.

## What

- 대상 POST: /api/agent, /api/agent/preparation, /api/agent/chat.
- 성공·인증 실패·입력 오류·충돌·서버 예외에도 서버가 생성한 ID를 반환한다.
- HTTP 재전송은 새 ID, 한 HTTP 요청의 모델 재시도는 같은 trace를 사용한다.

## How

ContextVar의 trace context를 route가 재사용하고 middleware finally에서 초기화한다. X-Trace-Id와 X-Request-Id는 같은 서버 생성 ID다. body.request_id는 멱등 키이며 HTTP ID와 구분한다. CORS expose로 브라우저 읽기를 허용한다. Langfuse http.request에는 ID·method·고정 path·status·latency만 기록한다. Authorization·본문·쿼리 문자열은 보내지 않는다. exporter 실패는 로그로 남기며 헤더 존재만으로 export 성공을 주장하지 않는다.

## AC

- Given 성공·오류 응답, When 헤더와 관측을 대조, Then trace ID가 일치한다.
- Given 동시 두 요청, When generation·summary를 기록, Then 서로 다른 요청 ID가 섞이지 않는다.
- Given 허용된 프런트 Origin, When fetch 응답 헤더를 읽음, Then trace ID를 얻는다.
- Given 운영 사이트의 실제 채팅 요청, When Observations API v2에서 해당 ID를 조회, Then http.request와 preparation.chat·provider 관측의 ID가 일치한다.
