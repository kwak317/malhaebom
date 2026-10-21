# 공통 JSON provider를 OpenAI SDK로 전환

## Why

직접 HTTP 요청하던 공통 LLM 호출을 SDK 기반으로 바꾸되 최신 main의 전송 정책과 서버 계약을 유지한다.

## Goal

공통 호출 한 곳을 OpenAI Python SDK로 전환한다. 모델·키·출력 계약·웹검색 전용 호출 및 DB 변경은 범위 밖이다.

## What

서버 문맥 조회 → Skill·출력 Schema 구성 → SDK Chat Completions → JSON 해석 → 서버 계약 검증 → API 응답.
코칭·면접 대화·README·공고 요구사항·검색 의도에서 사용하는 공통 provider에 적용한다.

## How

- 기존 의존성 `openai>=1.60,<2`와 설정을 사용한다. `max_retries=0`으로 SDK 자동 재시도를 막고 서버의 최대 1~3회 전송 시도·backoff·계약 repair 정책을 유지한다.
- `client.chat.completions.with_raw_response.create`로 호출해 HTTP 상태 및 원본 usage의 토큰·비용 값을 기존 로직에 전달한다.
- OpenRouter 옵션은 `extra_body`, 출력 한도는 `max_tokens`로 전달하며 GPT-5 strict Schema 변환을 유지한다. temperature는 추가하지 않는다.
- SDK 오류를 기존 402·429·타임아웃·연결 오류로 매핑하고 관측 메타데이터·비용 제한·JSON 검증을 유지한다.

## AC

- Given 기존 설정, When generate, Then 동일 endpoint·인증·메시지·strict Schema·토큰 한도가 전송된다.
- Given 402/429/5xx/타임아웃/연결 오류, When 호출, Then 기존 오류·전송 횟수·관측 규칙을 지킨다.
- Given SDK 자동 retry=0, When 서버 전송 한도=1, Then 503에도 실제 요청이 한 번이다.
- Given usage·정상/잘못된 JSON, When 응답 처리, Then 비용·토큰·서버 계약 검증 경계를 보존한다.
- 실제 계정·녹음·DB 브라우저 E2E와 각 외부 모델 소비자의 실시간 호출은 이번 PR의 테스트 증거에 포함하지 않는다.
