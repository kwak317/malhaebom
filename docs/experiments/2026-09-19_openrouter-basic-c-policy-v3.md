# C policy v3 Basic 전체평가

확정한 C 최소상황기준과 dataset v2(case14/18/21/22 Cpartial,20 Cmet)을 적용한다.
대상은 Basic3종×30case=90회, Premium0,재시도0. `.venv-llm-eval` Python3.12,
실행 당시 prompt label `coaching-output-v2`와 현재 Skill bundle/dataset/grader/schema source hash를 고정한다.
prompt 본문에는 확정한 C 정책이 포함되며, label은 실행 사실 그대로 보존한다.
strict JSONSchema,provider.require_parameters true,자동routing,temperature/reasoning 모델기본,
SDKretry0/max_calls1/concurrency6/read timeout60초 조건이다.

실행: `.venv-llm-eval/bin/python -B local-results/openrouter-basic-full-c-policy-20260919/execute.py --live`.
`--live`없이는90회계획만표시한다. case별완료파일을건너뛰므로중단후같은명령으로재개가능하다.
결과는기존평가와분리한 `local-results/openrouter-basic-full-c-policy-20260919/`에 저장한다.
`report.py`는offline으로all-attempts/summary/REPORT/failure-details/verification을생성한다.
완료후결과와Worklog를갱신한다. 사람semantic/critical은null, Premium은호출하지않는다.

## 결과

- 90/90 실행을 별도 디렉터리에 보존했다. Premium 0, retry 0이다.
- Qwen case 29는 약 12분간 반환되지 않아 중복 호출 없이 driver watchdog timeout으로 종료했다.
  이 1건은 품질 실패에서 제외했고 generation/provider/usage/cost는 미확인으로 남겼다.
- 계약 통과는 Qwen 24/30, DeepSeek 30/30, Gemini 30/30이다.
- 품질 통과/실패/인프라는 Qwen 14/15/1, DeepSeek 23/7/0, Gemini 25/5/0이다.
- 비용 확인 89건 합계는 $0.5464719216이다. Qwen 확인 29건 $0.079183534,
  DeepSeek 30건 $0.1012021376, Gemini 30건 $0.36608625이며 timeout 1건 비용은 알 수 없다.
- 사람 semantic 점수는 전부 null이고 제한된 자동 critical 검사는 0/9 탐지다.
- 상세 결과와 raw 출력은 `local-results/openrouter-basic-full-c-policy-20260919/`에 있다.
