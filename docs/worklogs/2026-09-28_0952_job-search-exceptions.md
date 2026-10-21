# Worklog — 경력 무관 표기와 채용 시 마감 공고 허용

- 일시: 2026-09-28 09:52 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 이번 요청은 로컬 수정이며 Issue·PR 등록 및 commit/push는 수행하지 않았다.
- 관련 요구사항/결정: 사용자 지정 두 예외; `docs/specs/saramin-backend-recommendations.md`

## 1. 목적

공백이 있는 `경력 무관`과 날짜 대신 `채용 시 마감`이 명시된 공고를 검색·원문 검증·카드 표시·선택 검증에서 허용한다. 종료된 공고와 불명확한 마감 정보는 계속 제외한다.

## 2. 작업 전 상태

- 대상 체크아웃: `proj2-3-complete-flow`, 브랜치 `codex/team-local-auth-18080`, HEAD `65aef86`. 기존 미커밋 작업이 다수 있어 해당 변경을 보존했다.
- 기존 검증은 경력 문자열에서 `경력무관`을 직접 검색하고 날짜만 파싱했다. `경력 무관`과 `채용 시 마감`은 거부됐다.
- 실행 API의 코드와 체크아웃의 관련 코드가 같았고, 웹은 기존 번들 `/assets/index-DxhT9pBy.js`를 제공했다.
- 기존 추천 테스트 30개와 프런트엔드 관련 두 파일 34개는 통과했다. 수정 전 회귀 사례를 추가해 백엔드 14개 실패(하위 사례 포함), 프런트엔드 2개 실패로 문제를 재현했다.
- 변경 전 455개 기존 파일의 해시·Git 상태와 대상 9개 파일 원본을 아래 경로에 보관했다. 환경변수나 비밀 파일은 복사하지 않았다.

```text
/var/folders/vp/7pp0r4tx0sz43lhc2tmlkmq00000gn/T/malhaebom-job-exceptions-20260928-352cdkoh
```

## 3. 수행 내용

1. 기존 Spec에 예외 조건, nullable 날짜 계약, 유지할 제외 조건과 AC를 먼저 반영했다.
2. 검색 질의에 `경력무관`·`경력 무관`을 함께 넣고 `채용 시 마감` 공고도 찾도록 검색 지시를 수정했다.
3. 두 출처의 경력 검사에서 공백을 정규화하고 마감일 필드의 명시적 `채용 시 마감`은 `None`으로 허용했다. 종료 안내·경력 제한·백엔드 업무 조건은 유지했다.
4. 필수 `deadline`을 날짜 또는 `null`로 변경했다. 카드의 `null`은 `채용 시 마감`으로 표시하고 같은 점수에서는 날짜 있는 공고를 먼저 정렬했다.
5. 두 출처의 표기 변형·종료·누락·미정·잘못된 날짜·지난 날짜·경력 제한, 추천 HTTP 계약·정렬과 선택 검증, 프런트엔드 계약·표시를 검증했다.
6. API와 웹 이미지를 재빌드하고 동일 로컬 Compose 서비스에 적용했다. 별도 18001 mock 컨테이너는 그대로 실행 중이다.

## 주요 판단과 이유

- 날짜를 임의로 만들지 않았다. `deadline=null`은 서버가 원문 마감 필드의 `채용 시 마감` 표기를 확인했을 때만 생성한다.
- `마감일 미제공`, 빈 값, `미정`을 날짜 없는 공고로 통과시키지 않았다. 이번 예외는 명시적 표기에 한정한다.
- `신입 제외 / 경력 무관`은 공백 정규화 후에도 거부한다. 검색 예외가 명시된 지원 제한을 우회하지 않도록 했다.
- 실제 외부 검색 모델·공고 페이지는 테스트 원문과 구분한다. 검색 결과 건수 증가를 이번 테스트만으로 보장하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/services/saramin_recommendation.py` | 경력 정규화, 검색어·검색 지시, 마감 파싱 예외, 날짜 없는 정렬 |
| `backend/app/schemas/saramin_recommendation.py` | 필수 nullable deadline 계약 |
| `backend/tests/test_saramin_recommendation.py` | 두 출처의 허용·거부 및 추천 HTTP·정렬 회귀 사례 |
| `frontend/src/api/practiceSetup.ts` | nullable deadline 타입·응답 검증 |
| `frontend/src/api/practiceSetup.test.ts` | null 허용·필수 필드 누락 거부 |
| `frontend/src/pages/PracticePage.tsx` | 날짜 없는 공고 마감 표시 |
| `frontend/src/pages/PracticeSetupFlow.test.tsx` | 날짜 있는 카드와 채용 시 마감 카드 표시 검증 |
| `docs/specs/saramin-backend-recommendations.md` | 예외 조건·응답 계약·AC |
| `docs/CURRENT_STATE.md` | 현재 동작과 검증 범위 |
| 이 Worklog | 실제 수행·검증 및 미확인 범위 |

## 5. 검증

격리된 백엔드 실행은 기존 API 이미지의 Python 런타임에 체크아웃을 읽기 전용으로 마운트하고 `--network none`, `--read-only`, `PYTHONDONTWRITEBYTECODE=1`을 적용했다. 호스트 비밀 환경변수를 전달하지 않았다.

```text
python -B -m unittest backend.tests.test_saramin_recommendation -q
35 tests: OK

python -B -m unittest discover -s backend/tests -p 'test_*.py' -q
299 tests: OK

frontend: npm test -- --run
22 files / 79 tests: passed

frontend: npm run build
TypeScript / Vite: passed

API_PORT=18000 WEB_PORT=18080 COMPOSE_PROJECT_NAME=proj2-3-complete-flow docker compose config --quiet
passed

동일 환경에서 docker compose build api frontend
passed

동일 환경에서 docker compose up -d --no-build api frontend
API / frontend: healthy

GET http://localhost:18000/health -> 200 {"status":"ok"}
GET http://localhost:18080/ -> 200
POST http://localhost:18080/api/job-search/recommendations without auth -> 401
```

- API 이미지: `sha256:3160344c0bad3b4f5b26f0e1eddae65d0a6b97848669d371298bf78e978cb28b`, 컨테이너 `d3c2584872be`.
- 웹 이미지: `sha256:af00cdb19ef87b8d47929285286963712205b42b451252e76c7ad425128e1107`, 컨테이너 `386b7a5cab13`, 제공 번들 `/assets/index-CI7bTWrF.js`.
- API 서비스·스키마 파일의 호스트와 컨테이너 SHA256 일치 확인.
- 실행 API 안에서 두 출처의 합성 원문을 검증했다. 모두 `experience="경력 무관"`, `deadline=null`로 통과했고 응답 스키마의 날짜 필드는 필수이며 date 또는 null이다. 외부 공고를 가져온 결과가 아니다.
- 별도 숨김 브라우저 탭에서 홈→연습 화면으로 진입했다. NCS 9개 목록·코치 화면 표시와 콘솔 error 0개, 스크린샷을 확인했다. 기존 사용자 탭의 채팅을 조작하지 않았다.
- 변경 전 455개 파일의 해시와 최종 파일을 비교했다. 대상 9개만 변경됐고 삭제된 파일은 없으며 새 파일은 이 Worklog 한 개다. 이번 추가 줄에 trailing whitespace가 없다. 기존 미커밋 작업은 보존됐다.

## 6. 발견한 문제 / 남은 리스크

- 새 검색어로 인해 기존 정확한 질의 문자열 검사 1개가 실패했다. 기대 질의를 갱신하는 중 일시적 들여쓰기 오류가 있었으나 수정 후 좁은 35개와 전체 299개 테스트가 통과했다.
- Docker 프런트엔드 빌드는 기존 잠금 의존성에서 npm audit 5개 취약점과 번들 크기 경고를 보고했지만 빌드는 통과했다. 의존성·잠금 파일은 이번 범위에서 변경하지 않았다.
- 기존 외부 검색의 402·504와 후보 원문 메타데이터 부족은 이 예외 수정과 별개다. 이번 변경은 모든 빈 결과 원인을 제거한다는 의미가 아니다.

## 미확인 사항

- 변경 후 실시간 외부 공고 검색, 실제 날짜 없는 공고의 브라우저 카드 표시 및 해당 공고의 AI 분석·저장은 재호출하지 않았다. 카드·계약·선택 원문 검증은 격리 테스트로 확인했다.
- 공급자가 `채용 시 마감`을 description의 마감 필드 밖에만 표시하는 경우나 다른 표현은 이번 예외 대상이 아니다.
- GitHub 등록·CI·통합·원격 배포는 수행하지 않았다.

## 7. 다음 작업

- 사용자가 기존 연습 탭을 새로고침한 뒤 같은 조건으로 다시 검색하면 변경된 검증·표시가 적용된다. 실시간 반환 건수와 외부 검색 오류는 그 호출 결과로 확인한다.
