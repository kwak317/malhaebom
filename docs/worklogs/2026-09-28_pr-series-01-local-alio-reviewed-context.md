# 로컬 변경 PR 이관 — add ALIO search and source-grounded practice context

- 원본 작업 기간: 2026-09-21~22
- 기준: main d3ecfaa, 마지막 머지 PR #69. 원본 체크아웃과 실행 서비스는 변경하지 않았다.
- 이번 범위: ALIO 검색 결과를 서버에서 다시 확인하고 원문 근거가 검증된 요구사항만 사용자별 공고·연습 문맥으로 저장한다.
- 평가셋·판정자, mock 호출, 프롬프트 설명 자료는 제외했다.
- 최신 main의 MCP, provider usage/cost 반환, cause 관찰·추론과 기존 관측 코드를 보존했다.
- 검증: 해당 커밋을 git archive로 추출한 별도 디렉터리에서 backend unittest 및 적용되는 frontend 테스트/빌드를 재검사한다. 결과는 PR 본문에 실제 수치를 기록한다.
- SQL 권한 검증: 로컬 적용 migration 기준 ALIO 11, 공공취업 6, 재정경제부 6, 민간 공고 8 pgTAP assertion 통과. 각 테스트와 임시 pgTAP extension은 transaction rollback했다. 원격 DB 적용은 수행하지 않았다.
- 통합 검증: backend 405 tests, frontend 79 tests, TypeScript/Vite build 통과. 외부 API/LLM·로그인 사용자 E2E는 이번 PR 이관에서 재호출하지 않았다.
- 사용자는 800줄 초과 기능 묶음을 이번 PR 생성에 한해 승인했다. 해당 크기 정책 검사 실패는 PR에 명시하고 머지하지 않는다.
- 다음 작업: 앞선 PR부터 팀 리뷰 후 순차 반영. 이 작업에서는 merge하지 않는다.
