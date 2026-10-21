# 로컬 변경 PR 이관 — add NCS self-check and grounded GitHub README analysis

- 원본 작업 기간: 2026-09-23
- 기준: main d3ecfaa, 마지막 머지 PR #69. 원본 체크아웃과 실행 서비스는 변경하지 않았다.
- 이번 범위: NCS 기준정보와 공개 GitHub README의 기술·흐름을 조회·분석한다. 원문 인용 검증과 주소 제한, 재시도 및 크레딧 오류 구분을 유지하며 개인 역량 판정으로 사용하지 않는다.
- 평가셋·판정자, mock 호출, 프롬프트 설명 자료는 제외했다.
- 최신 main의 MCP, provider usage/cost 반환, cause 관찰·추론과 기존 관측 코드를 보존했다.
- 검증: 해당 커밋을 git archive로 추출한 별도 디렉터리에서 backend unittest 및 적용되는 frontend 테스트/빌드를 재검사한다. 결과는 PR 본문에 실제 수치를 기록한다.
- SQL 권한 검증: 로컬 적용 migration 기준 ALIO 11, 공공취업 6, 재정경제부 6, 민간 공고 8 pgTAP assertion 통과. 각 테스트와 임시 pgTAP extension은 transaction rollback했다. 원격 DB 적용은 수행하지 않았다.
- 통합 검증: backend 405 tests, frontend 79 tests, TypeScript/Vite build 통과. 외부 API/LLM·로그인 사용자 E2E는 이번 PR 이관에서 재호출하지 않았다.
- 사용자는 800줄 초과 기능 묶음을 이번 PR 생성에 한해 승인했다. 해당 크기 정책 검사 실패는 PR에 명시하고 머지하지 않는다.
- 다음 작업: 앞선 PR부터 팀 리뷰 후 순차 반영. 이 작업에서는 merge하지 않는다.
