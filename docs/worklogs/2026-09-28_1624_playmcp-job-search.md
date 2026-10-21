# Worklog — PlayMCP 사람인 공고 검색 전환

- 일시: 2026-09-28 16:24 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 생성하지 않음
- 관련 요구사항/결정: 기존 방식 보존 후 PlayMCP로 바꿔 달라는 사용자 요청, [Spec](../specs/playmcp-job-search.md)

## 1. 목적

현재 로컬 공고 검색을 카카오 PlayMCP 사람인 도구 호출로 바꾸고 기존 웹검색으로 복귀할 수 있게 유지한다.

## 2. 작업 전 상태

- checkout: `proj2-3-complete-flow`, `codex/team-local-auth-18080`. 기존 미커밋 변경이 많아 관련 파일만 수정하고 초기 소스를 별도로 백업했다. commit/push/PR/merge 없음.
- 기존 API는 OpenRouter로 사람인·잡코리아를 검색했다. 호스트 mcporter 연결은 서비스에 연결되지 않았다.
- 기존 추천 테스트 35개가 변경 전에 통과했다.

## 3. 수행 내용

- Spec 작성 후 `PlayMcpSaraminSearch`와 서버 전용 token store를 추가했다. MCP 카드에서 허용된 사람인 개별 공고 URL만 정규화한다.
- 20건씩 1~2페이지로 검색을 제한한다. 기존 추천 서비스가 출처 수를 공급자에 맞춰 확인하게 변경해 사람인 3건이 있어도 잡코리아가 없다는 이유로 재검색하지 않는다.
- 공급자 factory에 `web`/`playmcp` 선택을 추가했다. 기존 웹검색 class 본문은 초기 백업과 정확히 일치한다.
- 기존 인증에서 필요한 값만 `.env.playmcp/auth.json`으로 복사했다. 파일 0600, 디렉터리 0700, Git/Docker 제외와 API 전용 mount를 확인했다. 원래 home mcporter 인증 파일은 변경하지 않았다.
- 공식 OAuth protected-resource/authorization-server metadata에서 token endpoint를 확인하고, 실제 갱신 HTTP 200·파일 저장·다음 읽기 재사용을 확인했다.
- 로컬 `.env`만 `playmcp`로 설정해 API만 `--no-deps`로 재빌드했다. frontend 컨테이너 `a097d23271ce`와 이미지가 유지됐다. 새 API는 `ebb7616ee9e1`, healthy다.

## 주요 판단과 이유

- 현재 모드는 사람인만 조회하며 자동 웹검색 fallback을 두지 않는다. 사용자에게 검색 출처 축소를 작업 중 명시했다.
- 기존 MCP Python SDK를 재사용하므로 의존성 추가/ML 패키지 재설치 없음. 토큰은 별도 writable 디렉터리에 원자적으로 갱신하며 이미지에 넣지 않는다.
- README와 NCS 원문을 MCP에 전송하지 않는다. 내부 원문 검증·근거 매칭은 유지한다.
- 개인 연결을 이용한 단일 API 프로세스 로컬 시도이며 운영 계정·다중 worker 저장 방식은 이번 범위 밖이다.

## 4. 변경 파일

- `backend/app/services/playmcp_job_search.py`: MCP 호출, 안전한 URL 추출, 인증/갱신/실패 처리.
- `backend/app/services/saramin_recommendation.py`: 공급자 선택과 공급자별 출처 개수. 기존 웹검색 본문 보존.
- `backend/tests/test_playmcp_job_search.py`: 11개 연결·필터·만료·복귀·실패 테스트.
- `.env.example`, `docker-compose.yml`: 비밀값 없는 설정 예시와 API 인증 디렉터리 mount.
- `docs/specs/playmcp-job-search.md`, `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, 본 Worklog.
- Git 제외 로컬 변경: `.env`, `.env.playmcp/auth.json`, `.env.bak-playmcp-20260928`. 인증값을 문서/증빙에는 저장하지 않았다.

## 5. 검증

```text
docker run --rm --network none -v "$PWD:/app:ro" --entrypoint python proj2-3-complete-flow-api -m unittest discover -s backend/tests -p 'test_saramin_recommendation.py' -q
35 tests PASS
동일 격리 명령의 test_playmcp_job_search.py: 11 tests PASS
동일 격리 명령의 전체 backend/tests: 331 tests PASS
docker compose config --quiet: PASS
docker compose up -d --build --no-deps api: PASS
/health 200, /practice 200, 실제 미인증 추천 POST 401
```

- 신규 테스트: 허용 URL·중복 제거, 정상 빈 widget과 응답 오류 구분, 만료 token 갱신·권한·저장, secret 없는 오류, timeout, 401 제한 재시도, 고정 도구 호출, 불필요한 2차 출처 검색 방지, 기존 공급자로 복귀.
- 실제 MCP 공개 `백엔드` 검색: 후보 20건, 약 0.41초(원문 검증 전).
- 재빌드한 API 이미지에서 TestClient와 테스트 인증을 사용한 실제 추천 API: `selected_ncs_ids=["skill-server"]`, HTTP 200, 원문 검증된 사람인 공고 3건, 약 33.758초. 사용자 DB에는 저장하지 않았다.
- host/컨테이너 `playmcp_job_search.py` SHA256: `f0213e163ff22cc05b05397310f2224c2b8db884032d23e2bab39eea18e817a9`.
- 증빙: workspace 루트의 `output/mcp/playmcp-switch-20260928/api-verification.json`, `before/`, `before-sha256.json`. 초기 `.env` 백업에는 민감값이 있으므로 Git 제외 0600 파일로만 보관한다.
- 초기 host Python의 OAuth metadata 조회는 로컬 TLS trust 오류였다. TLS 검증을 끄지 않고 system curl 및 실제 Docker httpx의 TLS 검증으로 공식 metadata HTTP 200을 확인했다.

## 6. 발견한 문제 / 남은 리스크

- 검색 호출 자체는 짧지만 원문 조회/검증이 전체 시간을 차지한다. 전체 요청 시간을 0.41초로 표현하지 않는다.
- MCP의 경력 0 조건만으로 신입 공고라고 보장할 수 없어 기존 원문 신입 조건 검증을 유지한다.
- 다중 worker/여러 클라이언트의 refresh token 회전 공유, 서비스 운영 이용조건은 이번 로컬 검증 대상이 아니다.

## 미확인 사항

- 실제 로그인 사용자 브라우저에서 NCS 선택부터 공고 카드 표시까지, README 포함 검색, 선택/저장·녹음·코칭·재답변 E2E.
- 같은 입력·네트워크·반복 횟수로 측정한 웹검색 대비 p50/p95 및 속도 개선 배수.
- 현재 토큰의 자연 만료 이후 자동 갱신은 아직 경과하지 않았다. 갱신 endpoint 실호출과 코드의 만료 분기는 각각 검증했다.

## 7. 복귀 방법

로컬 `.env`의 `JOB_SEARCH_PROVIDER=web`으로 바꾼 뒤 `docker compose up -d --no-deps api`를 실행한다. 소스 삭제나 프런트 재빌드 없이 기존 사람인·잡코리아 웹검색을 사용한다.

## 8. 후속 속도 개선 — 16:25~16:31

사용자가 작업 중 `최대한 빨리 공고 찾아오게`를 요청했다. 초기 33.758초에서 느린 원문을 모두 기다리는 경로를 확인했다.

- PlayMCP에만 `return_when_ready`를 적용했다. 최대 6개의 병렬 조회 결과를 완료 순으로 처리하며 원문 검증·근거 매칭·중복 제거를 통과한 서로 다른 3건을 확보하면 반환한다. 아직 시작하지 않은 future는 취소하고 진행 중인 HTTP 요청은 백그라운드에서 끝난다. 남은 요청에도 3초 connect/read HTTP timeout을 적용하며 전체 요청 시간의 상한 3초를 보장한다는 뜻은 아니다.
- 조기 반환만 적용한 실제 검색은 2.606초였지만 실행 이미지의 재측정은 17.534초였다. 외부 응답 변동을 숨기지 않고 후보 대기 순서와 timeout을 추가로 조정했다.
- 원격 카드에서 신입·경력무관으로 표시된 URL을 우선한다. 다른 후보를 제거하지 않으며 표시만으로 허용하지 않는다. 원문 신입·마감·업무 조건과 근거 매칭은 그대로 검사한다.
- PlayMCP만 원문 timeout 3초, MCP 전체 요청 8초로 제한했다. 기존 웹검색의 원문 timeout 8초와 전체 후보 평가 방식은 유지한다. 느린 원문은 이번 검색에서 제외될 수 있다.
- 최종 코드 전체 backend 334개 PASS(11.508초), 신규 연결·속도 테스트 14개 포함. 느린 앞 후보를 기다리지 않음, 미검증·미매칭·중복 공고가 3건에 포함되지 않음, 카드 표시는 순서만 변경함을 검사했다.
- 최종 실제 서비스 호출: 1.778초, 검증된 사람인 공고 3건. 최종 실행 이미지의 TestClient·테스트 인증 API: HTTP 200, 7.795초, 검증된 사람인 공고 3건, 웹검색 미호출. 입력은 둘 다 `skill-server`이며 README 없이 실행했다.
- 최종 API `f37767e6a9c9`, 이미지 `sha256:395f2773a7c765f90b598db9c8b09890c7c9c72578abac2a93663aa0ab93e7b6`, healthy. 기존 frontend `a097d23271ce` 유지, API health·연습 화면 HTTP 200.
- 최종 host/컨테이너 해시: `playmcp_job_search.py` `20a8ab39348d0e9d5226d488a591b1033d0e59e95a15fc17bde1b4724a4f87c2`, `saramin_recommendation.py` `93e661f21f31567b8e96b1ea8083fe2d9818e16d08e9edb9025646462c9a098c`.
- 증빙 디렉터리에 `fast-api-before-prioritization.json`, `prioritized-service-verification.json`, `current-api-verification.json`을 추가했다. 초기 단계의 증거는 보존한다.
- 실제 인증 파일을 찾지 못하는 API는 503과 민감값 없는 안내를 반환하고 웹검색을 호출하지 않음을 실행 이미지에서도 확인했다. `.env.playmcp/auth.json`이 이미지 `/app`에 존재하지 않음을 확인했다.

같은 입력의 소수 실시간 측정이며 안정적 p50/p95 또는 항상 2초 이내라는 보장은 아니다. 최종 조회 범위는 사람인이고 로그인 브라우저/README 포함 E2E는 아직 실행하지 않았다.
