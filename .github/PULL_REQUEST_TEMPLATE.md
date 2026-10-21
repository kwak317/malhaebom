## 1. 이 PR의 목적 (Summary)
<!-- 무엇을 왜 바꿨는지, 해결하려는 목적을 명확히 2~3줄로 설명 -->

## 2. 주요 변경 사항 (Key Changes)
<!-- 코드, 설정, 문서 등 변경 핵심 요약 -->

## 3. Review-size 분석 (Review Core & Exceptions)
<!--
  - Total diff: (e.g. +150 / -20)
  - Review-core diff: (e.g. 170 lines)
  - Exception / Supporting files: (e.g. Worklog 80 lines, lockfile 500 lines)
-->
- Total diff: 
- Review-core: 
- Exception diff: 

<!-- Review-core가 400줄을 초과하거나 전체 작업이 큰 경우 아래 항목 필수 작성 -->
### 기준 초과(또는 대규모 PR) 사유 및 분리하지 않은 이유
<!--
  - 왜 하나의 논리적 작업인지 / 분리 시 리뷰가 어려워지는 이유:
  - reviewer가 점진적으로 볼 수 있는 commit 구성 안내:
-->

## 4. 검증 결과 (Verification)
<!-- 실행한 테스트 명령어, 수동 확인 결과, PR policy check 결과 등 -->
- [ ] 로컬 또는 CI에서 관련 테스트/검증 통과 (`python3 -m unittest ...` 등)
- [ ] PR size policy check 통과 (`python3 scripts/check_pr_policy.py`)
- [ ] 의미 있는 변경에 대한 `docs/worklogs/` Worklog 작성 또는 갱신
- [ ] 필요 시 `CURRENT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md` 갱신

## 5. 체크리스트 & 머지 안내
- [ ] 하나의 PR = 하나의 명확한 목적 유지
- [ ] merge 전 다른 팀원 1명 이상의 approve를 받음
- [ ] merge 직전 최신 main rebase / merge 상태 및 테스트 재확인 후 PR 작성자가 최종 merge
