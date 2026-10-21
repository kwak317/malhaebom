# 코칭 실패 지점 기록

## Why

최종 실패 종류만으로는 JSON 파싱·출력 검증·저장 실패와 재시도 이력을 구분하기 어렵다.

## Goal

`POST /api/agent`의 실패 단계·오류 코드·모델 호출 횟수·시도별 실패 이력을 기록한다. 아래 AC를 모두 통과한다. 재시도 정책, 사용자 응답, 실제 모델 호출·배포는 변경 범위 밖이다.

## What

- 문맥 조회, 모델 호출, JSON 파싱, 출력 검증, 결과 저장 실패를 구분한다.
- 보정 후 성공해도 앞선 실패 이력을 보존한다.
- 호출 전 실패는 계약 시도 0회, 보정 요청까지 호출하면 계약 시도 2회·재시도 1회다. transport 재시도는 기존 generation 관측의 `transport_attempt`로 구분한다.
- 동시 요청의 기록을 분리한다. 관측 전송 실패는 로컬 로그에 남긴다.

## How

- 요청별 ContextVar와 공유 가능한 진단 객체를 사용해 FastAPI worker thread에서 기록한다.
- `failure_stage`, `error_code`, `attempt_count`, `retry_count`, `attempt_failures`를 기존 Langfuse metadata에 추가한다.
- 실패 이벤트는 표준 logging에도 남긴다. 원문, 토큰, 임의 예외 메시지·stack trace는 기록하지 않는다.
- 최신 GitHub의 파싱·출력 검증 보정과 transport 재시도 정책을 유지한다. 성공한 보정은 최종 실패 상태를 해제하되 앞선 실패 이력을 보존한다.

## AC

1. GIVEN 계약 시도 한도로 1회를 설정한 잘못된 JSON, WHEN 분석, THEN parse 단계·고정 오류 코드·시도 1회·재시도 0회를 기록하고 HTTP 502를 유지한다. 기본 보정 정책에서는 다음 시도와 이전 파싱 실패 이력을 보존한다.
2. GIVEN 잘못된 인용 후 정상 출력, WHEN 보정 성공, THEN 성공 응답과 시도 2회·재시도 1회·첫 검증 실패 이력을 기록한다.
3. GIVEN 문맥/모델/저장 실패, WHEN 분석, THEN 각 단계와 고정 오류 코드, 실제 호출 횟수를 기록한다.
4. GIVEN 동시 요청, WHEN 각 요청이 실패하거나 성공, THEN 이력이 다른 요청에 섞이지 않는다.
5. GIVEN 민감한 예외 메시지와 관측 장애, WHEN 실패 기록, THEN 고정 코드만 로컬 로그에 남기고 사용자 응답을 유지한다.
