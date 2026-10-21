# Worklog — 공고 검색 빈 결과와 실패 처리 수정

- 일시: 2026-09-27 19:30 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음. 원격 Issue 생성·push·PR은 이번 로컬 수정 범위에 포함하지 않았다.
- 관련 Spec: [백엔드 공고 후보 추천](../specs/saramin-backend-recommendations.md)

## 1. 목적

공고 검색에서 불필요하게 좁아진 검색어를 수정하고, 검색 응답 미완료·보완 검색 실패를 공고 없음으로 표시하지 않는다. 변경을 로컬 API에 반영하고 실제 검색과 관련 회귀 테스트로 확인한다.

## 2. 작업 전 상태

- 사용자 스크린샷의 공고 검색 요청은 API 로그에서 200이었다. 당시 단계별 로그가 없어 그 요청의 정확한 빈 결과 원인은 소급 확정하지 않았다.
- 로컬 소스와 실행 중인 API의 검색 서비스 파일 해시가 같았다. 오래된 이미지 불일치가 원인은 아니었다.
- 검색 재현에서 200 응답인데 본문이 null이고 URL citation이 0건인 사례가 있었다. 원문 확인 가능한 공고도 다른 검색에서는 반환됐다.
- 사용자가 제공한 공개 README는 https://github.com/5Headers/team_project_backend 이다. 원문 검증을 통과한 분석에서 앞 두 기술이 Spring Boot와 MySQL이었다. 기존 보완 검색은 이를 `"Spring Boot MySQL"`이라는 하나의 정확한 문구로 묶었다.
- 날짜를 `"2026-09"`처럼 정확한 문구로 요구하고 있었다. 보완 검색 오류를 무시한 채 최종 결과가 비면 정상 빈 목록을 반환하는 경로도 확인했다.
- 기존 사용자 변경 111개가 있었으며 수정 대상 원본을 `/tmp/malhaebom-job-search-20260927-backup-192304`에 백업했다.

## 3. 수행 내용

- 앞 두 README 기술을 별도 보완 검색 질의에 사용한다.
- 검색어에서 마감월의 정확한 문자열 일치 요구를 제거한다. 오늘·이번 달·다음 달을 지시문에 유지하고 현재 원문의 마감일을 다시 검사한다.
- 검색에만 모델이 지원하는 reasoning.effort=low를 적용하고 기존 출력 상한을 유지한다.
- 인용 없이 length/tool_calls로 끝나거나 본문이 null인 응답을 한 번 재시도한다. 여전히 미완료이면 검색 오류로 반환한다.
- 최종 후보가 없고 보완 검색이 실패했으면 503 오류를 반환한다. 이미 검증한 공고가 있으면 부분 결과를 유지한다.
- 빈 결과 로그에 후보 수와 원문 검증 통과 수를 남긴다. 사용자 입력·README·자격 증명은 새 운영 로그에 넣지 않는다.
- URL 허용 목록, 원문 재조회, 마감·신입·백엔드 조건, 근거 겹침, 중복 제거, 선택 전 저장 금지 및 인증 계약은 유지했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| backend/app/services/saramin_recommendation.py | 검색어 분리, 날짜 검색 조건, 미완료 응답·보완 검색 실패 처리, 빈 결과 진단 |
| backend/tests/test_saramin_recommendation.py | 검색 조건·실패·부분 결과 회귀 테스트 및 API 503 확인 |
| docs/specs/saramin-backend-recommendations.md | 동작과 수용 기준, native 검색 횟수 제한의 실제 범위 |
| docs/CURRENT_STATE.md | 이번 실행 결과와 검증 범위 |
| docs/worklogs/2026-09-27_1930_job-search-empty-results.md | 본 기록 |

## 5. 검증

- 수정 전 백업 서비스와 새 회귀 테스트를 별도 Docker 컨테이너에서 실행했다. 3개 테스트 메서드에서 4개 assertion 실패로 기술 문구 결합·미완료 응답·보완 오류 무시를 재현했다.
- 수정 후 관련 테스트: 30개 통과. null 본문, length/tool_calls 종료, 재시도, 기존 인용 유지, 보완 실패의 503 전달, 이미 확인한 부분 결과 유지 포함.
- backend 전체 테스트: 294개 통과. 운영 키·환경을 주입하지 않은 별도 Docker 컨테이너에서 `--network none`으로 실행했다.
- `docker compose config --quiet` 통과. API만 `API_PORT=18000 WEB_PORT=18080 COMPOSE_PROJECT_NAME=proj2-3-complete-flow docker compose up -d --build api`로 재빌드했다.
- 웹 200, API /health 200, 웹 프록시의 비인증 공고 검색 POST는 401. api·frontend 컨테이너 healthy.
- 수정한 검색 서비스의 호스트/실행 컨테이너 SHA-256은 모두 `7bb8616a4167ed2ef282b46f1f7e3bde9ab518b97de3f48136812c66064145eb`였다.
- 제공 README의 현재 SHA·원문 인용을 재검증하고 selected_ncs_ids=['skill-server']로 실제 서비스 전체 검색을 실행했다. 85.7초 뒤 레데브의 진행 중인 공고 1건을 반환했다. 마감일 2026-09-29, https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=54613682. README 기술 직접 일치는 없고 선택 NCS 서버 구현 항목의 근거가 확인됐다.
- 실제 검색에는 native 일부의 504와 제한된 재시도가 있었다. Exa 200 응답과 원문 검증까지 실행했으며, 검증된 부분 결과는 반환됐다.
- OpenRouter 공식 검색·reasoning 문서를 참고하고 현재 모델 metadata에서 low 지원을 확인했다. Google native의 max_uses는 내부 검색 횟수 상한 보장이 아니므로 문서의 보장 표현을 수정했다.

## 6. 발견한 문제 / 남은 리스크

- 검색 인용, 원문 접근, 마감 상태에 따라 0~3건과 지연은 변한다. 없는 공고나 원문에서 확인할 수 없는 근거로 수를 채우지 않는다.
- 최초 README 재분석 1회는 크레딧 관련 오류로 실패했고 후속 요청에서 근거 검증을 통과했다. 당시 빈 검색 요청이 계정 크레딧 부족이었다고 단정하지 않는다.
- Google native 내부 검색 횟수·비용은 max_uses/max_tool_calls 값만으로 확정 상한을 입증하지 않았다. 공식 문서: https://openrouter.ai/docs/guides/features/server-tools/web-search , https://openrouter.ai/docs/guides/best-practices/reasoning-tokens .

## 미확인 사항

- 사용자는 README 링크만 답해 원래 선택한 NCS 항목은 확인하지 못했다. 실제 재검증의 NCS 조건은 skill-server이다.
- 사용자 Safari 화면의 재검색 클릭은 Computer Use 권한이 없어 직접 수행하지 못했다. 실제 서비스 호출과 API 계약 테스트를 로그인 브라우저 E2E로 표현하지 않는다.
- 선택 후 요구사항 저장·녹음·2차 비교는 이번 작업의 검증 범위 밖이다. 인증·DB 정책·migration은 변경하지 않았다.
- commit·push·PR·원격 Issue는 수행하지 않았다. 발견한 결함의 원격 Issue 등록은 별도 승인이 필요하다.

## 7. 다음 작업

- 사용자 현재 채팅에서 다시 검색을 눌러 같은 선택 조건의 결과를 확인한다. 계속 0건이면 새 단계별 로그로 후보 부족과 원문 검증 탈락을 구분한다.
