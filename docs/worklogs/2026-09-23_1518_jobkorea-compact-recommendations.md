# Worklog — 잡코리아 공고 추가와 추천 카드 축약

- 일시: 2026-09-23 15:18 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 Spec: [백엔드 공고 후보 추천](../specs/saramin-backend-recommendations.md)

## 1. 목적

사람인에 더해 잡코리아의 현재 신입 백엔드 공고를 찾고, 교차 출처 중복을 제거하며, 카드에는 README·NCS와 실제 겹치는 짧은 이유만 표시한다.

## 2. 작업 전 상태

- `POST /api/job-search/recommendations`는 사람인 개별 공고만 검색·검증했다.
- 공고 카드가 README 기능 흐름 원문과 검색 근거 발췌, 선택 NCS 여러 항목을 길게 보여줬다.
- 관련 파일을 포함한 작업 트리에 다른 미커밋 변경이 많았다. 이 작업의 범위만 수정했다.

## 3. 수행 내용

- 두 사이트를 별도 웹검색으로 조회하고 citation은 두 사이트의 개별 공고 URL만 허용했다. 잡코리아는 숫자 공고 ID를 고정 모바일 URL로 정규화해 현재 페이지 메타데이터·본문·마감일·신입 조건을 검증한다.
- 검증된 후보를 점수순으로 정렬하고 기업명과 유사 직무명을 비교해 교차 출처 중복을 제거했다. 서로 다른 공고가 있으면 출처별 한 건을 포함한다.
- README 기술 또는 기능 키워드 최대 하나와 선택 NCS 일치 항목 최대 하나를 카드의 `추천 이유`로 보여주고 긴 인용은 제거했다. README를 제출했으나 공고 원문과 일치한 항목이 없으면 그 상태를 명시한다. 이 카드의 폭·간격·패딩을 줄였다.
- 실제 브라우저에서 잡코리아의 사이트 로그인 안내가 README 기능과 잘못 일치하는 현상을 발견했다. 추천용 기능 키워드에서 일반적인 `로그인`을 빼고, 잡코리아 본문을 `나와의 적합도` 앞까지만 사용하도록 고쳤다.

## 주요 판단과 이유

- 웹검색 citation은 오래된 공고가 섞이므로 검색 결과만으로 추천하지 않고 원문을 다시 확인한다.
- 한 출처의 검색이 실패해도 다른 출처의 검증 공고는 표시한다. 외부 검색 장애가 전체 결과를 가리지 않게 하기 위함이다.
- 팀 README만으로 개인 구현 범위를 확정하지 않고, 실제 공고 원문과 겹친 항목만 표시한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/services/saramin_recommendation.py`, `backend/tests/test_saramin_recommendation.py` | 잡코리아 검색·검증·중복 제거와 회귀 테스트 |
| `frontend/src/pages/PracticePage.tsx`, `frontend/src/styles/practice-page.css`, `frontend/src/pages/PracticeSetupFlow.test.tsx` | 간결한 추천 이유·작은 카드와 화면 테스트 |
| `docs/specs/saramin-backend-recommendations.md`, `docs/CONSTRAINTS.md`, `docs/ARCHITECTURE.md`, `docs/CURRENT_STATE.md`, 이 Worklog | 기능 범위·서비스 경계·현재 동작과 검증 기록 |

## 5. 검증

```text
docker run --rm -v "$PWD/backend:/app/backend" proj2-3-complete-flow-api python -m unittest discover -s backend/tests -p 'test_*.py'
266 tests OK (환경변수를 주입하지 않은 격리 컨테이너)

npm test -- --run
76 tests OK

npm run build
통과

docker compose up -d --build api frontend
두 서비스 healthy
```

- 실제 웹검색에서 두 사이트의 개별 공고 citation을 받았다. 잡코리아 `49965430`과 사람인 `54871744`는 원문 기준 진행·신입 백엔드 공고로 확인했다. 검색 결과와 마감 상태는 실행 시점에 따라 바뀔 수 있다.
- 지정된 공개 README의 SHA와 원문 근거를 다시 확인한 서비스 호출에서 두 사이트 공고가 각각 추천 결과에 포함됐다. 이 호출의 분석 객체는 실제 README의 문구로 구성한 검증 입력이며 Gemini 출력 자체는 아니다.
- 로그인 브라우저에서 지정 README를 Gemini로 실제 분석한 뒤 검색 카드에 잡코리아 공고가 표시되는 것을 확인했다. 첫 화면에서 발견한 사이트 로그인 문구 오탐은 수정 후 실제 원문 검증에서 사라졌고, 관련 단위 테스트에 회귀 사례를 추가했다.
- 수정 후 같은 로그인 브라우저에서 재검색 200 응답으로 잡코리아 공고 카드 2건을 확인했다. 두 카드의 짧은 이유에는 선택 NCS만 있었고 잘못된 README 로그인 일치는 없었다. 최종 프런트엔드는 README 일치 항목이 없다는 표시를 추가했으며, 이 표시는 컴포넌트 테스트와 production build로 확인했다.
- Compose 환경변수를 그대로 주입한 전체 백엔드 테스트는 기존 코칭 환경 설정과 테스트 fixture가 충돌해 5 failures, 1 error였다. 동일 소스의 격리 컨테이너에서는 266개 모두 통과했다.

## 6. 발견한 문제 / 남은 리스크

- 외부 웹검색 결과와 원문 메타데이터는 언제든 바뀔 수 있다. 원문에서 README 기술을 확인할 수 없는 공고는 NCS 일치 항목과 README 일치 근거 부재를 표시한다.
- 검색 후보는 검토된 코칭 공고로 자동 저장·연결되지 않는다.

## 미확인 사항

- 외부 배포 환경에서의 동작과 채용 사이트의 향후 HTML 변경은 확인하지 않았다.

## 7. 다음 작업

- 제공자 응답이나 원문 구조가 바뀌면 허용 URL·검증 파서를 실제 샘플로 다시 확인한다.
