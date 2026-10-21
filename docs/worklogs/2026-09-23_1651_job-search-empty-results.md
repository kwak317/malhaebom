# Worklog — 공고 검색 빈 결과 재현과 후보 보강

- 일시: 2026-09-23 16:51 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 Spec: [백엔드 공고 후보 추천](../specs/saramin-backend-recommendations.md)

## 1. 목적

채팅의 `현재 검색에서 확인된 백엔드 공고가 없어요` 화면을 재현하고, 확인 가능한 공고가 검색·역량 겹침 단계에서 불필요하게 빠지는 문제를 수정한다.

## 2. 작업 전 상태

- API 로그에서 해당 공고 검색 요청은 200이었다. README 분석도 200이었으며 이번 빈 결과는 이전의 OpenRouter 402와 다르다.
- 실제 서비스 재현에서 native 기본 검색 URL citation은 0건, 보완 검색은 1건이었다. 보완 후보는 원문 검증에서 제외됐다.
- 별도 실제 검색에서는 추가 후보 중 신입·마감 조건을 통과한 잡코리아 공고가 있었으나, 제목의 `백엔드`를 제외한 상세 본문만으로 NCS 겹침을 검사해 최종 0건이 됐다.

## 3. 수행 내용

- 기본·보완 검색 후 3건 미만 또는 한 출처만 남았을 때 두 도메인으로 제한한 Exa 웹검색을 최대 1회 추가했다. 검색 결과는 기존 URL 허용 목록, 원문 재조회, 마감·신입 조건, 중복 제거를 그대로 거친다.
- 확인된 공고 제목과 상세 본문을 함께 사용해 README·NCS 겹침을 검사한다.
- 관련 명세·아키텍처·현재 상태를 갱신하고 API 이미지를 재빌드했다.

## 주요 판단과 이유

- 검색 모델의 200 응답에도 개별 공고 인용이 0건일 수 있어 다른 검색 엔진으로 후보를 보강했다. 검증하지 못한 공고를 결과 수 맞추기에 사용하지 않는다.
- 원문 메타데이터에서 확인된 공고 제목은 서버가 검증한 공고 정보이므로 `백엔드` NCS 근거로 사용할 수 있다. README 기술과 직접 일치하지 않는 경우는 별도로 표시한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/services/saramin_recommendation.py` | Exa 후보 보강, 제목 포함 근거 검사 |
| `backend/tests/test_saramin_recommendation.py` | 추가 검색 및 제목 근거 회귀 테스트 |
| `docs/specs/saramin-backend-recommendations.md` | 빈 결과 원인과 수용 기준 |
| `docs/ARCHITECTURE.md` | 웹검색 보강·검증 흐름 |
| `docs/CURRENT_STATE.md` | 실제 재현과 검증 범위 |
| `docs/worklogs/2026-09-23_1651_job-search-empty-results.md` | 본 기록 |

## 5. 검증

```text
docker compose up -d --build api
API 컨테이너 healthy

docker compose exec -T api python -m unittest tests.test_saramin_recommendation
19개 통과

docker compose exec -T api env -u COACHING_LLM_MODEL -u COACHING_PROVIDER -u COACHING_LLM_API_KEY -u OPENROUTER_API_KEY -u MCP_INTERNAL_SECRET python -m unittest discover -s tests
281개 테스트 결과 OK (테스트 프로세스의 자식 프로세스 종료 지연은 별도 관찰)

실제 공개 README + skill-server + 원문 검증 + Exa 추가 검색
후보 4건에서 검증된 잡코리아 공고 1건 반환, README 기술 직접 일치는 없음
```

## 6. 발견한 문제 / 남은 리스크

- 실제 계정 환경에서 전체 테스트를 그대로 실행하면 코칭 설정이 테스트의 mock 경로를 가로채 5개 실패·1개 오류가 발생한다. 코칭 설정을 제외한 격리 실행은 281개 OK였다. 이번 공고 검색 변경과는 다른 테스트 환경 문제다.
- 실시간 검색과 원문 접근 가능 여부에 따라 반환 건수는 달라진다. 검색이 0건인 모든 상황을 없앤 것은 아니다.

## 미확인 사항

- 열린 브라우저의 현재 채팅에는 공고 카드 2건이 보였다. API 재빌드 후 `다시 검색`을 누르지는 않았으므로 그 카드가 새 검색 경로로 생성됐는지는 확인하지 않았다. 실제 사용자 선택에는 `knowledge-data`와 `skill-server`가 있었으며, 새 검색 경로의 실제 호출 검증은 `skill-server`만 사용했다.

## 7. 다음 작업

- 실제 로그인 화면에서 `다시 검색` 후 카드 표시 여부를 확인한다. 공고가 다시 비면 검색 단계별 citation·원문 검증 건수를 확인한다.
