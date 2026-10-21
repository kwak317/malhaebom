# Worklog — 사람인 웹검색 기반 백엔드 공고 후보

- 일시: 2026-09-23 14:25 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 Spec: [사람인 백엔드 공고 후보 추천](../specs/saramin-backend-recommendations.md)

## 1. 목적

NCS 자기점검과 선택적으로 제출한 GitHub README를 바탕으로, 채팅에서 현재 모집 중인 사람인 백엔드 공고를 웹검색해 후보로 표시한다.

## 2. 작업 전 상태

- 기존 공공 채용 API 검색 결과에는 사용자가 찾는 백엔드 공고가 부족했다.
- NCS 선택과 README 분석·건너뛰기 채팅은 있었으나 사람인 웹검색과 추천은 연결되지 않았다.

## 3. 수행 내용

- OpenRouter `openrouter:web_search`의 Google native 검색으로 사람인 개별 공고 링크를 찾는다.
- 검색 인용의 Google 경유 URL은 한 번만 해석하고 허용된 사람인 개별 공고 주소만 조회한다.
- 공고 원문에서 기업명·직무명·마감일·신입 지원 가능 여부를 다시 확인하고, 기술·프로젝트 흐름·NCS 문구와 겹치는 근거를 표시한다.
- README SHA와 인용 원문, 선택 NCS ID를 서버에서 재검증한다. README를 건너뛰면 NCS 선택으로만 검색한다.
- 검색 중 표시, 후보 카드, 빈 결과·오류 및 재검색을 채팅에 추가했다. 검색 완료 시 새 추천 메시지로 스크롤한다. 결과는 기존 검토된 공고 DB나 코칭 문맥에 자동 반영하지 않는다.

## 주요 판단과 이유

- 사람인 공식 API 키가 현재 환경에 없고 사용자가 웹검색을 요구했으므로, 기존 서버의 OpenRouter 키로 웹검색을 호출한다.
- 검색 인용만으로 접수 중인 공고라고 단정하지 않고 현재 사람인 원문을 다시 조회한다.
- 팀 README는 개인 기여의 증거가 아니므로 기술·흐름의 겹침만 표시한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/services/saramin_recommendation.py`, `backend/app/schemas/saramin_recommendation.py`, `backend/app/main.py` | 웹검색, 원문 검증, 인증 API |
| `frontend/src/api/practiceSetup.ts`, `frontend/src/pages/PracticePage.tsx`, `frontend/src/styles/practice-page.css` | 추천 요청 및 채팅 표시 |
| `backend/tests/test_saramin_recommendation.py`, `frontend/src/api/practiceSetup.test.ts`, `frontend/src/pages/PracticeSetupFlow.test.tsx` | 검색·검증·화면 회귀 테스트 |
| `docs/specs/saramin-backend-recommendations.md`, `docs/CONSTRAINTS.md`, `docs/ARCHITECTURE.md`, `docs/CURRENT_STATE.md`, `README.md` | 설계 경계와 현재 상태 기록 |

## 5. 검증

```text
백엔드 전체 단위 테스트: 262개 통과 (중립 환경 Docker 이미지)
프런트엔드 전체 테스트: 76개 통과 (22개 파일)
프런트엔드 production build: 통과
로컬 Docker Compose: API·frontend healthy
실제 OpenRouter 웹검색 인용: 6건, 이 중 현시점 사람인 원문 검증에서 신입 공고 2건 확인
로컬 브라우저: NCS 3개 선택 → 지정 README 분석 → 사람인 추천 카드 2건 표시 확인
  - 드림어스컴퍼니 `rec_idx=55090664`: 신입, 2026-10-22 마감, Spring Boot·MySQL 겹침
  - 이너버스 `rec_idx=54871744`: 신입, 2026-09-25 마감, MySQL 겹침
최종 Compose 이미지: README 건너뛰기 → NCS만으로 검색 요청 확인. 첫 검색 503 뒤 재검색은 200·검증 후보 0건으로 빈 결과 안내와 사람인 전체 검색 링크가 표시됐다.
```

## 6. 발견한 문제 / 남은 리스크

- 웹검색과 모델 응답은 시점에 따라 다른 인용을 반환하므로 후보가 0건일 수 있다. 사용자는 재검색하거나 사람인 전체 검색 링크로 직접 확인할 수 있다.
- 첫 README 분석 요청은 원문 인용 검증에 실패해 503을 반환했고, 화면의 `다시 분석`으로 재시도하자 200과 분석 결과를 받았다. 모델 출력에 따른 간헐 실패 가능성이 남아 있다.
- 최종 이미지의 첫 NCS 조회와 README 건너뛰기 뒤 첫 웹검색도 각각 503을 반환했다. 재시도로 NCS는 정상 표시됐으며, 웹검색은 정상 응답했지만 검증 후보가 0건이었다. 빈 결과와 오류를 구분하고 재시도 UI를 표시하는 것은 확인했다.
- 외부 배포와 사람인 후보를 검토된 코칭 공고로 선택하는 경로는 이번 범위에서 검증하지 않았다.

## 7. 다음 작업

- 외부 배포 시 실제 OpenRouter 웹검색과 사람인 원문 접근을 별도로 확인한다.
