# 사람인 MCP + Tavily 잡코리아 공고 검색

## 목적

사람인 PlayMCP 검색을 유지하면서 잡코리아 공고 후보를 Tavily로 찾아 같은 추천 카드에 표시한다.

## 작업 전 상태

- 로컬 `.env`의 `JOB_SEARCH_PROVIDER=playmcp`는 사람인만 검색했다. `web` 모드는 사람인·잡코리아를 OpenRouter로 검색했다.
- 추천 서비스의 URL 허용 목록과 원문 검증기는 사람인·잡코리아를 이미 지원했다.
- 작업 폴더에는 이 기능과 무관한 미커밋 변경이 다수 있었다. 해당 변경을 보존했다.

## 수행 내용과 판단

- 별도 `playmcp_tavily` 모드에서 두 검색을 병렬 실행하고 실패를 출처별로 분리했다. 기존 모드의 동작은 유지했다.
- Tavily에는 고정된 백엔드 신입 검색어와 잡코리아 도메인 제한만 보낸다. README/NCS 원문은 전송하지 않는다.
- Tavily 응답은 잡코리아 개별 공고 URL 후보만 남긴다. 검색 요약을 공고 내용으로 사용하지 않고 기존 원문 검증을 재사용한다.
- 두 출처의 검증된 결과가 있으면 최대 3건에서 빠르게 반환한다. Tavily 키가 없는 상태에서 새 모드를 선택하면 설정 오류를 낸다.
- 변경 파일: `backend/app/services/tavily_job_search.py`, `backend/app/services/saramin_recommendation.py`, `backend/tests/test_tavily_job_search.py`, `.env.example`, `docs/specs/playmcp-tavily-jobkorea-search.md`, `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md`, 이 Worklog.

## 검증

- 네트워크 차단 Docker 단발 컨테이너에서 `test_tavily_job_search`, `test_playmcp_job_search`, `test_saramin_recommendation` 59개 통과. 유효·악성 URL, 공급자 부분/전체 실패, 혼합 카드, 키 누락을 확인했다.
- 공개 잡코리아 개별 공고 `GI_Read/49831064`를 현재 원문 검증기로 조회해 신입 백엔드 공고로 검증됨을 확인했다. 이는 Tavily 검색 성공 증거가 아니다.
- `py_compile`과 변경 파일의 `git diff --check` 통과.
- 사용자가 키를 로컬 `.env`에 설정한 뒤 단발 컨테이너에서 실제 외부 검색·원문 검증으로 잡코리아 1건과 사람인 2건을 얻었다.
- `JOB_SEARCH_PROVIDER=playmcp_tavily`로 전환해 API 이미지를 빌드·교체했다. 새 이미지의 관련 테스트 59개 통과, API·프런트엔드 healthy, `/health`·프런트 페이지 HTTP 200을 확인했다. 실행 컨테이너에서도 같은 유형의 검증 카드 3건(잡코리아 1, 사람인 2)을 얻었다.

## 발견한 문제·미확인 사항·다음 작업

- 로컬 `.env`의 키는 Git에서 제외된다. 키 값은 출력·Worklog에 기록하지 않았다.
- 브라우저 연습 페이지는 열렸지만 자동화에서 NCS 역량 선택 버튼의 상태가 바뀌지 않아 로그인 사용자 화면의 카드 렌더링과 공고 선택 후 저장까지는 검증하지 못했다. 이는 버튼 자체의 제품 결함으로 확인된 것은 아니다.
- 실제 검색은 두 번의 단발 호출이며 결과·지연·비용의 안정성을 보장하지 않는다. 사용자 세션에서 화면 카드 표시와 공고 선택 경로를 이어서 확인할 수 있다.
