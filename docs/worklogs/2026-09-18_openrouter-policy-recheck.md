# Worklog — 新Skill Basic27회 API정책 재검증

- 일시:2026-09-18
- 작업자/에이전트:Codex
- 사용자승인:9case×Basic3종만,총27회. Premium미호출.
- 관련실험:[정책재검증](../experiments/2026-09-18_openrouter-policy-recheck.md)

## 1. 목적

새Skill의intent독립/Vpartial/not_observed근거정책이 실제응답에서반영되는지 점검한다.

## 2. 작업 전 상태

정렬grader와30casev2는이미검증완료,기존252건원본/regrade별도보존.
9공통실패case01/04/06/14/16/18/20/21/22를사용하며기존uncommitted변경보존.

## 3. 수행 내용

전용Python3.12로총27회실API,SDKretry0/max_calls1/concurrency3/timeout60(readtimeout),
strict JSONSchema/provider.require_parameters true/자동routing/temperature및reasoning기본을유지했다.
.env는overrideFalse로로딩,OpenRouter개인키만사용했고값미출력.
새Skill전체bundle와coaching-output-v2,현재v2/grader를사용했다.
case별raw/usage.cost/token(reasoning/cache포함)/provider/generation/schema/validator/latency를즉시저장했다.
별도로컬폴더에서보고서를생성하고이전동일9case의정렬grader결과와비교했다.
intent/V raw진단은계약실패응답까지포함하되공식계약통과로간주하지않았다.

## 주요 판단과 이유

불완전응답도과금보존했고Premiumfallback/재시도/추가모델조회는하지않았다.
Qwen의긴응답과DeepSeek일부provider의read keepalive로wall latency가60초를넘었지만설정변경/중복요청없이완료했다.
reason원문분석은AI분석초안이며사람semantic0~2로채우지않았다.

## 4. 변경 파일

- `local-results/openrouter-policy-recheck-20260918/`:execute.py/report.py/manifest/source-snapshot/records/all-attempts/summary/REPORT/policy-output-review/common-failures/basic-failure-set/verification.
- `docs/experiments/2026-09-18_openrouter-policy-recheck.md`,본Worklog,`docs/CURRENT_STATE.md`완료기록.
- dataset/grader/schema/Skill/모델config 추가수정없음. 기존raw/regrade파일변경없음.

## 5. 검증

```text
.venv-llm-eval/bin/python -B local-results/openrouter-policy-recheck-20260918/execute.py
dryplan:27Basic/Premium0/retry0.
같은명령 --live :27/27완료. 인프라/API오류0. 요청반복0.
.venv-llm-eval/bin/python -B local-results/openrouter-policy-recheck-20260918/report.py
offline리포트/검증성공.
27고유generation/attempt,모두Basic/call1,raw/provider/usage.cost/latency존재.
reasoning/cache usage27/27존재;정책sourcehash불변;기존252raw SHA256불변;semantic null.
```

이작업은로컬실험driver/보고서만추가했고프로덕션코드변경없어전체unit 재실행없음.
정렬작업의전체226테스트통과기록을유지한다. commit/PR/push없음.

## 6. 결과 / 남은 리스크

실제총비용$0.1766286997. Qwen$0.023554696/DS$0.0500195037/Gem$0.1030545.
계약Qwen7/9,DS9/9,Gem9/9. 품질실패8/6/6. evidence문장/원문충실성은계약통과응답100%.
rawintent7/9,8/9,9/9;04/16/18행위Vpartial1/3,3/3,3/3.
Qwen01결과누락intent감점,04/18Vmet,20비백엔드CAV감점이남았다.
공통실패14/18/20/21/22의C 최소상황정보 경계는독립정답검토대상.
Qwen04비활성actiontargetID,14related공고evidence누락이별도계약오류.
9선택case/모델별1회라최종30건성능순위/반복안정성/통계적개선을확정할수없다.
자동표본외critical/사람semantic은null. 제한된자동지표통과가의미품질전체인증은아니다.

## 7. 다음 작업

C경계/독립label검토와semantic사람검토를API없이우선수행가능.
전체30건비교및Premium추가는별도사용자지시전미실행.
