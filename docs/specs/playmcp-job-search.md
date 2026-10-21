# PlayMCP 사람인 공고 검색 전환

## Why

LLM 웹검색을 거치는 기존 민간 공고 검색을 PlayMCP 사람인 도구 직접 호출로 바꿔 사용해 본다. 기존 방식은 삭제하지 않고 복귀할 수 있게 보존한다. 속도 개선은 동일 조건의 측정 전까지 확정하지 않는다.

## Goal

- 현재 로컬 `POST /api/job-search/recommendations`를 PlayMCP로 전환하고 원문 검증된 최대 3건을 기존 채팅에 반환한다.
- `JOB_SEARCH_PROVIDER=web` 한 줄로 기존 사람인·잡코리아 웹검색을 선택할 수 있다. 예시/미설정 기본값은 `web`이다.
- PlayMCP 모드는 사람인만 조회한다. 자동 웹검색 우회, 잡코리아 MCP, UI 변경, DB 변경, 공개 배포는 제외한다.

## What

- NCS 선택 → README 분석/건너뛰기 → FastAPI → 사람인 MCP → 개별 공고 URL 추출 → 기존 마감·신입·백엔드·README/NCS 원문 검증 → 기존 카드.
- 인증 파일 누락/잘못된 형식: 503과 재시도 안내, 웹검색을 호출하지 않는다.
- 만료 접근 토큰: refresh token으로 한 번 갱신하고 서버 전용 파일에 저장한다. 갱신 실패/401 재실패: 인증 안내와 503.
- 도구 오류/시간 초과/잘못된 응답: 503. 정상 빈 카드 목록은 빈 결과로 구분한다.
- 원격 widget은 실행하지 않고 `apply` 액션의 허용된 사람인 개별 공고 URL만 추출한다. 외부 주소·목록 링크·중복은 제외한다.
- 원문 검증 결과가 3건 미만이면 다음 페이지를 한 번 더 조회한다. 추가 조회 실패 시 이미 검증한 결과를 유지하고, 결과가 전혀 없으면 오류를 표시한다.
- 후속 속도 요청: PlayMCP에서는 원문 검증·근거 매칭·중복 제거를 통과한 3건을 확보하면 반환한다. 먼저 도착한 결과를 사용하며 느린 앞쪽 후보나 모든 후보의 순위 확정을 기다리지 않는다. 시작하지 않은 검증은 취소하고 진행 중인 요청은 기존 HTTP timeout 안에 종료된다. 기존 웹검색의 전체 후보 평가 방식은 유지한다.
- 카드에 신입·경력무관 표시가 있는 URL을 먼저 조회한다. 표시는 순서에만 사용하고 다른 후보를 제거하거나 원문 검증을 대신하지 않는다. PlayMCP 원문 조회 timeout은 3초다. 느린 원문은 후보에서 제외될 수 있다.

## How

- 기존 API 요청·응답·인증·선택 후 원문 재검증/요구사항 인용 검증 계약은 유지한다.
- 기존 `mcp>=1.29,<2` Python SDK의 Streamable HTTP 클라이언트를 사용한다. 새 의존성 없음.
- gateway: `https://playmcp.kakao.com/mcp`, 도구: `SaraminMcp-search_saramin_jobs`.
- `백엔드`, 관련도 순, 페이지당 20건, 페이지 1~2. 토큰은 backend만 읽으며 README·NCS 원문은 MCP에 전송하지 않는다.
- 서버 전용 `PLAYMCP_AUTH_FILE`: `access_token`, `refresh_token`, `expires_at`(Unix seconds), `client_id`를 가진 JSON. 로컬 `.env.playmcp/`는 Git/Docker 이미지에서 제외되고 API에만 volume으로 연결한다. 파일 0600, 디렉터리 0700.
- 갱신 endpoint는 공식 OAuth metadata의 `https://playauth.kakao.com/playmcp/oauth2/token`. 갱신은 단일 API 프로세스 내 잠금, 원자적 파일 저장으로 처리한다. 다중 worker/공용 운영 계정은 이번 범위 밖이다.
- MCP 전체 요청 제한 8초, token HTTP 제한 15초. 실패 로그에는 오류 종류만 기록하며 token/원격 응답 원문은 노출하지 않는다.

## AC

- Given `web`/미설정, When 공급자 생성, Then 기존 웹검색 객체를 사용한다.
- Given `playmcp`와 인증 파일, When 공급자 생성, Then OpenRouter 키 없이 MCP 공급자를 사용한다.
- Given 정상 MCP 카드, When 추출, Then 개별 공고 URL만 정규화·중복 제거하고 원문 검증을 거쳐 카드 최대 3건을 반환한다.
- Given 악성 URL/목록 링크/widget 액션, When 추출, Then 허용되지 않은 링크와 동작을 사용하지 않는다.
- Given 만료 토큰, When 검색, Then 갱신 후 재사용할 인증값을 0600 파일로 저장한다. 실패 시 secret을 포함하지 않는 오류를 반환한다.
- Given 기존 인증 파일의 mode가 0600이 아님(예: 0644), When 토큰 조회/강제 갱신, Then 파일 내용 읽기와 갱신 요청 전에 거부한다. mode는 임의로 변경하지 않는다.
- Given MCP 오류/시간 초과/잘못된 응답, When 검색, Then 웹검색을 호출하지 않고 503을 반환한다.
- Given 검증된 3건의 사람인 후보, When 추천, Then 잡코리아가 없다는 이유로 추가 검색하지 않는다.
- Given 앞 후보의 원문 조회가 느리고 다른 3건이 검증·근거 매칭·중복 제거를 통과할 때, When 추천, Then 느린 후보의 종료를 기다리지 않고 3건을 반환한다. 미검증·중복 후보는 완료 개수에 포함하지 않는다.
- Given 카드의 신입·경력무관 표시, When 검증 순서를 정할 때, Then 해당 URL을 우선하되 원문에서 다시 확인한다. 기존 웹검색 timeout은 8초로 유지한다.
- Given 인증 없는 요청, When API 호출, Then 기존처럼 401을 반환한다.
