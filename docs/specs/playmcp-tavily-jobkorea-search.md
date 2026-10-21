# PlayMCP 사람인 + Tavily 잡코리아 공고 검색

## Why

- 사람인 PlayMCP 모드는 사람인 공고만 보여 준다. 신입 백엔드 준비생이 잡코리아 공고도 같은 검색 화면에서 비교할 수 있게 한다.
- 검색 결과는 공고 후보일 뿐이므로, 현재 원문에서 모집 상태와 직무 조건을 확인해야 한다.

## Goal

- `JOB_SEARCH_PROVIDER=playmcp_tavily`에서 사람인 MCP와 잡코리아 Tavily 검색을 함께 실행한다.
- 기존 API·화면 계약을 유지하며 원문 검증과 NCS/README 근거 매칭을 통과한 최대 3건만 표시한다.
- 한 검색 공급자가 실패해도 다른 공급자의 검증된 공고를 보여 준다.
- Out of Scope: 잡코리아 외 새 사이트, Tavily 검색 요약을 공고 요구사항으로 사용, DB/UI 변경, 실제 외부 호출이 없는 상태의 운영 성공 주장.

## What

- FastAPI는 사람인 MCP와 Tavily를 병렬 호출한다. Tavily에는 고정된 잡코리아 검색어만 보내고 사용자 README/NCS 원문은 보내지 않는다.
- Tavily 결과에서는 허용된 잡코리아 개별 공고 URL만 정규화한다. 목록·다른 도메인·중복 링크는 버린다.
- 기존 원문 검증기가 사람인·잡코리아의 마감일, 신입/경력무관, 백엔드 상세, 선택 근거를 확인한다. 검증 실패 후보는 카드에 넣지 않는다.
- 한 공급자 실패 시 다른 공급자의 결과를 계속 처리한다. 둘 다 실패하면 기존 503 오류를 반환한다.
- 결과가 3건 미만이면 기존 사람인 MCP 다음 페이지를 한 번 조회한다. 잡코리아 재검색은 하지 않는다.
- Tavily 키가 없으면 `playmcp_tavily` 모드로 API를 시작하지 않고 설정 오류를 낸다. 기존 `playmcp`·`web` 모드는 유지한다.

## How

- Tavily Search API `POST /search`: `include_domains=["jobkorea.co.kr"]`, `max_results=10`, 검색 요약·원문 응답 불필요.
- `TAVILY_API_KEY`는 API 서버 환경변수로만 전달한다. 비밀값이나 Tavily 응답 원문을 로그에 남기지 않는다.
- `PlayMcpTavilyJobSearch`가 두 검색 결과를 기존 추천 서비스의 `url` 후보 목록으로 전달한다. 추천 서비스는 두 출처의 검증 결과가 있으면 최대 3건에서 빠르게 반환한다.
- 사용자가 카드를 선택할 때 기존 `verify_for_review`와 공고 요구사항 인용 검증을 다시 적용한다.

## AC

- Given Tavily가 유효한 잡코리아 URL과 다른 링크를 반환할 때, When 검색할 때, Then 개별 잡코리아 URL만 정규화·중복 제거한다.
- Given 두 공급자가 각각 검증 가능한 공고를 반환할 때, When 추천할 때, Then 두 출처의 카드가 최대 3건에 포함된다.
- Given 한 공급자가 실패할 때, When 다른 공급자에 검증 가능한 공고가 있을 때, Then 해당 공고를 표시한다.
- Given 두 공급자가 모두 실패할 때, When 추천할 때, Then 기존 검색 불가 오류를 반환한다.
- Given `playmcp_tavily`에 키가 없을 때, When 공급자를 생성할 때, Then 설정 오류가 발생한다.
- Given 검색 결과가 마감·경력 전용·본문 누락 공고일 때, When 원문 검증할 때, Then 카드에 표시하지 않는다.
