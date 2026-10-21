# Worklog — NCS 백엔드 역량 자기점검 채팅

- 일시: 2026-09-23 12:30 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 Spec: [채팅 시작 시 백엔드 개발 역량 선택](../specs/ncs-backend-competency-chat.md)

## 1. 목적

연습 채팅 시작 시 백엔드 개발에 관련된 지식·기술·태도 선택지를 하나의 코치 메시지로 제공하고, 사용자가 보유했다고 생각하는 항목을 현재 채팅에 표시한다.

## 2. 작업 전 상태

- 루트 `.env`에 `NCS_API_KEY`가 설정되어 있었지만 채팅이나 서버의 NCS 호출 경로는 없었다.
- NCS 기준정보 `NCS005`는 능력단위명·정의를 제공하며 KSA 구분 필드는 제공하지 않는다. 사용자는 NCS 능력단위를 조회하고 검토된 KSA 선택지를 별도로 연결하는 방식을 선택했다.
- 저장소에는 다른 작업의 미커밋 변경이 다수 있어 해당 변경을 보존했다.

## 3. 수행 내용

- 서버 전용 `GET /api/ncs/backend-competencies`에 기존 Bearer 인증을 적용했다. 서버가 NCS 응용SW엔지니어링 최신 능력단위를 조회하고 직무 분류·사용 여부·능력단위 코드와 정의를 확인한다.
- 검토된 능력단위 8개에 자기점검 선택지 9개를 연결했다. KSA 문구는 말해봄이 작성한 내용임을 채팅에 명시했다.
- 프런트엔드 채팅 시작 메시지에 지식·기술·태도 각 3개와 NCS 근거·출처를 표시했다. 복수 선택 후 `선택 완료`를 누르면 선택한 항목을 사용자 메시지에 한 번 표시한다.
- 키 누락·제공자 오류·근거 누락은 선택지를 추정하지 않고 오류·재시도로 처리한다. 로그아웃 상태에서는 NCS 조회 없이 로그인 안내를 표시한다.
- 코칭 점수, 공고 요구사항, DB 저장에는 이 선택을 연결하지 않았다.

## 주요 판단과 이유

NCS 기준정보의 능력단위와 제품이 작성한 KSA 자기점검 문구를 분리해, 사용자에게 공식 원문과 해석을 혼동시키지 않도록 했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/services/ncs_competency.py`, `backend/app/schemas/ncs_competency.py` | NCS 조회·검증·응답 모델 |
| `backend/app/main.py`, `.env.example` | 인증된 API 라우트와 서버 환경변수 예시 |
| `frontend/src/api/practiceSetup.ts`, `frontend/src/pages/PracticePage.tsx`, `frontend/src/styles/practice-page.css` | API 요청과 채팅 선택 UI |
| `backend/tests/test_ncs_competency.py`, `frontend/src/api/practiceSetup.test.ts`, `frontend/src/pages/PracticeSetupFlow.test.tsx`, `frontend/src/pages/PracticeConversationFlow.test.tsx` | 조회·인증·실패·선택 회귀 테스트 |
| `docs/specs/ncs-backend-competency-chat.md`, `docs/CURRENT_STATE.md`, 이 Worklog | 범위와 현재 동작 기록 |

## 5. 검증

```text
docker run --rm --network none --entrypoint python proj2-3-complete-flow-api:latest -m unittest discover -s backend/tests -q
250 tests passed

npm test -- --run src/pages/PracticeSetupFlow.test.tsx src/pages/PracticeConversationFlow.test.tsx src/api/practiceSetup.test.ts
3 files / 28 tests passed

npm run build
TypeScript 및 Vite production build passed

docker compose build api frontend
두 이미지 빌드 통과

docker compose run --rm --no-deps --entrypoint python api -c '...NcsCompetencyService...'
실제 NCS API 응답에서 응용SW엔지니어링 선택지 9개 확인

docker compose up -d --no-deps api frontend
API와 프런트엔드 로컬 컨테이너 재생성, API healthy

curl http://127.0.0.1:18080/api/ncs/backend-competencies (인증 없음)
401 확인

로컬 브라우저 http://127.0.0.1:18080/practice
로그인 세션에서 9개 항목·NCS 근거 표시, 범주별 1개씩 선택 후 사용자 채팅 메시지에 3개만 표시 확인
```

## 6. 발견한 문제 / 남은 리스크

- NCS 제공자의 향후 능력단위 개정으로 검토된 코드가 사라지면 선택지가 표시되지 않고 재시도 오류가 나온다. 이때 연결 항목을 다시 검토해야 한다.
- `agent-browser` CLI가 설치되어 있지 않아 Codex 브라우저 UI로 화면을 확인했다.

## 미확인 사항

- 외부 배포 환경과 별도 사용자 계정의 로그인 흐름은 확인하지 않았다. 로컬 Docker 이미지에는 현재 작업 트리의 다른 미커밋 변경도 포함된다.

## 7. 다음 작업

- NCS 능력단위가 개정되면 연결 문구의 적합성을 검토한다.
