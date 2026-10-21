# Worklog — 공고 검색 표시와 일시 오류 재시도

- 일시: 2026-09-23 14:51 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 Spec: [공고 검색 후보](../specs/saramin-backend-recommendations.md)

## 1. 목적

사용자가 본 검색 503 오류를 조사하고, 채팅에 노출되는 검색 출처 이름을 `공고 검색`으로 바꾼다.

## 2. 작업 전 상태

- 채팅 제목·오류·재검색 버튼과 API 경로에 특정 검색 출처 이름이 노출됐다.
- 로컬 API 로그에서 추천 요청이 503을 반환한 것은 확인됐지만 상위 연결 실패 원인은 남지 않았다.

## 3. 수행 내용

- 채팅 제목·진행·오류·링크·버튼 문구를 출처 이름 없는 공고 검색 문구로 바꿨다.
- 호출 경로를 `POST /api/job-search/recommendations`로 바꾸고 화면 CSS 클래스도 검색 기능 이름으로 정리했다. 검색 대상과 검증 규칙 자체는 유지했다.
- 웹검색 상위 서비스가 408·429·5xx를 반환하거나 연결/시간 초과가 나면 한 번 자동 재시도한다. 상태 코드나 예외 종류만 서버 로그에 남기고 인증키는 기록하지 않는다.

## 주요 판단과 이유

- 검색 출처의 실제 구현은 문서에 남긴다. 화면 명칭 변경이 검색 범위 확대로 오인되지 않게 한다.
- 503이 재현됐을 때 서버 로그는 `ConnectError` 2회였고, 같은 시점 컨테이너에서 `openrouter.ai` DNS 조회가 `[Errno -5] No address associated with hostname`으로 실패했다. 자동 재시도는 짧은 연결 장애에만 대응하며 외부 DNS 장애 자체를 해결하지는 못한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `frontend/src/pages/PracticePage.tsx`, `frontend/src/api/practiceSetup.ts`, `frontend/src/styles/practice-page.css` | 사용자 문구·API 호출 경로·화면 클래스 |
| `backend/app/main.py`, `backend/app/services/saramin_recommendation.py` | API 경로·오류 문구·일시 오류 재시도·진단 로그 |
| `backend/tests/test_saramin_recommendation.py`, `frontend/src/pages/PracticeSetupFlow.test.tsx`, `frontend/src/api/practiceSetup.test.ts` | 재시도와 중립 문구·경로 검증 |
| `docs/specs/saramin-backend-recommendations.md`, `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md` | 실제 동작·경계 갱신 |

## 5. 검증

```text
백엔드 단위 테스트 전체: 263개 통과
프런트엔드 테스트 전체: 76개 통과
프런트엔드 production build: 통과
로컬 Compose 재빌드: API·프런트엔드 실행
로컬 브라우저: 새 채팅 제목·진행 문구·오류 문구·재검색 버튼에 출처 이름이 없음을 확인
DNS 복구 후 로컬 브라우저: `POST /api/job-search/recommendations` 200, 신입 백엔드 공고 카드 1건과 `공고 원문 확인` 링크 표시
```

## 6. 발견한 문제 / 남은 리스크

- 로컬 브라우저 첫 검색은 두 번의 DNS `ConnectError`로 503을 반환했다. 이후 같은 컨테이너에서 외부 도메인 DNS 조회가 다시 성공했고 재검색은 200 및 공고 카드 1건을 반환했다.
- 검색 결과와 접수 상태는 호출 시점에 따라 변한다. 현재 사용자가 본 실패가 영구적으로 해결됐다는 근거는 없다.

## 7. 다음 작업

- 외부 DNS 장애가 반복되면 실행 환경의 DNS 상태를 별도로 점검한다.
