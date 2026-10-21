# 새 Skill 기준 Basic27회 정책 재검증

사용자 승인 범위: case01/04/06/14/16/18/20/21/22 × qwen/qwen3.8-flash,
deepseek/deepseek-v4.1-flash,google/gemini-3.8-flash. 총27회,Premium0/재시도0.
전용Python3.12 `.venv-llm-eval`,dataset.v2,coaching-output-v2 및현재Skill로 실행한다.
strict JSONSchema,require_parameters true,자동routing,temperature/reasoning 모델기본 유지.

로컬독립결과 `local-results/openrouter-policy-recheck-20260918/`에 manifest/source-snapshot,
case별comparison.json,usage실제cost/provider/raw/validation/latency를 보존한다.
재현: `.venv-llm-eval/bin/python -B local-results/openrouter-policy-recheck-20260918/execute.py --live`.
기존case파일을 건너뛰므로재현전체새실행은새디렉터리에script를복사한다. `--live`없으면계획만출력한다.
보고서는같은폴더report.py 실행(offline)로생성한다. 이전동일9case 응답은 정렬grader의
regrade-policy-aligned결과를 비교참조하며 새호출/비용집계에 합치지 않는다.

정책 준수는intent/V expectedlabel일치와원문확인으로검토한다. 사람semantic/critical은null이며
9건 선택파일럿을 전체30건 모델선정 결과로확대하지 않는다. case당1회라consistency미측정.
실행완료후아래결과 및Worklog를 갱신한다.

## 완료 결과

27회완료,API/인프라오류0,재시도0,Premium0. usage.cost실제총액 $0.1766286997.
Qwen contract/schema/validator7/8/7,DeepSeek9/9/9,Gemini9/9/9(모델별9회).
품질실패8/6/6(이전동일9case정렬grader는9/9/9실패).
raw intent정답7/9,8/9,9/9; 04/16/18확인행위Vpartial1/3,3/3,3/3.
공통실패9→5:14,18,20,21,22. 모두 Cpartial 이하로보는 최소상황정보 기준경계가남았다.
새Skill에서주요정책은Gemini와DeepSeek V에선개선, Qwen01/04/18/20에서정책미준수잔존.
9건선택표본1회이므로전체30건순위/consistency를 확정하지 않는다.
27고유generation/raw/provider/usage.cost/reasoning/cache usage/latency 모두보존,
정책소스전후hash및기존252건rawhash불변검증통과. 사람semantic/critical은null.
[Worklog](../worklogs/2026-09-18_openrouter-policy-recheck.md), 로컬REPORT.md참조.
