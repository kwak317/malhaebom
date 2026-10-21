# Worklog — GitHub README Gemini 분석과 채팅 입력 표시

- 일시: 2026-09-23 13:25 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 Spec: [GitHub README 분석](../specs/github-readme-gemini-analysis.md)

## 1. 목적

NCS 역량을 선택한 사용자가 제출한 공개 GitHub README에서 기술 스택과 프로젝트 기능 흐름을 추출해 채팅에 표시한다. 분석 중에는 작은 말풍선의 움직이는 점 3개를 보여준다.

## 2. 작업 전 상태

- 연습 채팅은 역량 선택 뒤 README 링크를 요청하고 링크를 사용자 메시지로 표시했지만 README 내용은 읽지 않았다.
- 제공된 `https://github.com/5Headers/team_project_backend` 저장소의 공개 `README.md`가 GitHub API에서 조회되는 것을 확인했다.
- 기존 서버에는 OpenRouter 호환 구조화 JSON provider와 서버 전용 `OPENROUTER_API_KEY` 설정이 있었다.

## 3. 수행 내용

- 인증된 `POST /api/github/readme/analyze`를 추가했다. 서버가 HTTPS GitHub 저장소 또는 README 파일 URL을 제한적으로 파싱하고 GitHub REST API에서 공개 README를 가져온다.
- `google/gemini-3.8-flash`로 기술 스택·기능 흐름을 추출한다. 출력 형식과 원문 인용 포함 여부를 검사하고, 인용 불일치 시 한 번 재시도한다.
- 링크 제출 뒤 채팅에 입력 중 점 3개, 결과·원문 근거, 오류·재시도·주소 수정 동작을 추가했다. 긴 결과는 카드의 시작 지점으로 스크롤한다.
- 팀 README에 적힌 기술을 개인이 직접 구현했다는 판단으로 표시하지 않도록 안내했다.

## 주요 판단과 이유

- README 조회는 서버의 고정된 `api.github.com` 호스트로만 보냈다. 클라이언트가 보낸 URL을 직접 요청하지 않는다.
- README 분석은 DB 저장이나 면접 코칭 평가 입력에 연결하지 않았다. 공개 팀 문서는 개인 기여의 증거가 아니기 때문이다.
- 모델이 원문과 맞지 않는 인용을 반환하면 추측 결과를 표시하지 않고 오류로 처리한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/schemas/github_readme.py` | 요청·구조화 분석 응답 스키마 |
| `backend/app/services/github_readme_analysis.py` | GitHub README 조회, Gemini 호출, 원문 근거 검증 |
| `backend/app/main.py` | 인증된 분석 API 라우트 |
| `backend/tests/test_github_readme_analysis.py` | URL·조회·근거·인증·실패 테스트 |
| `frontend/src/api/practiceSetup.ts`, `frontend/src/api/practiceSetup.test.ts` | 분석 API 클라이언트와 계약 테스트 |
| `frontend/src/pages/PracticePage.tsx`, `frontend/src/pages/PracticeSetupFlow.test.tsx` | 제출·입력 중 표시·결과·재시도와 화면 테스트 |
| `frontend/src/hooks/useCoachThreadAutoScroll.ts`, `frontend/src/hooks/useCoachThreadAutoScroll.test.tsx` | 긴 분석 결과 카드 시작 위치로 이동 |
| `frontend/src/styles/practice-page.css` | 결과 카드와 입력 중 점 3개 스타일 |
| `docs/specs/github-readme-gemini-analysis.md`, `docs/ARCHITECTURE.md`, `docs/CURRENT_STATE.md` | 기능 계약·서비스 경계·현재 동작 기록 |

## 5. 검증

```text
docker run --rm proj2-3-complete-flow-api:latest python -m unittest discover -s backend/tests -p 'test_*.py' -q
257 tests OK (Compose 환경변수를 주입하지 않은 격리 환경)

npm test
74 tests passed

npm run build
TypeScript/Vite production build passed

로컬 Docker Compose + 로그인 브라우저
NCS 선택 → 제공된 GitHub URL 제출 → 점 3개 입력 중 표시 → Gemini 결과와 근거 표시 확인
긴 결과 카드의 시작 지점으로 스크롤 확인
```

## 6. 발견한 문제 / 남은 리스크

- Compose `.env`를 주입한 백엔드 전체 테스트는 기존 코칭 테스트 5개 실패·1개 오류가 발생했다. 관련 테스트가 Compose의 코칭 설정값을 가정하지 않는 문제로 보이며, 동일 이미지의 환경변수 없는 격리 실행에서는 전체 257개가 통과했다. 이번 기능 파일 외의 코칭 경로는 변경하지 않았다.
- 실제 Gemini 호출 한 차례는 두 번 모두 README와 일치하지 않는 인용을 반환해 오류와 재시도 동작으로 이어졌다. 다른 실제 호출에서는 검증된 결과가 표시됐다. 모델 응답 변동으로 재시도가 필요할 수 있다.

## 미확인 사항

- 외부 배포 환경의 인증·네트워크 동작과 비공개 저장소는 검증하지 않았다.
- README만으로 특정 사용자의 구현 범위·기술 숙련도는 확인할 수 없다.

## 7. 다음 작업

- 운영에서 원문 인용 실패 빈도를 관찰하고 필요하면 README의 Markdown 표기 차이와 실제 내용 차이를 구분해 검증 규칙을 보완한다.
