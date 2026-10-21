# OpenRouter Basic smoke — 계정 ZDR 정책 차단

- 목적: 승인된 실제 smoke에서 응답/검증/provider/usage/cost 저장을 확인하고, 통과한 경우만 Basic 3종 전체 30건 평가.
- 결과: smoke 실패. Qwen case 02가 HTTP 404이며 `zdr-violation-by-account`로 provider endpoint 1개 제외. 모델 미지원/키 무효로 해석하지 않는다.
- 환경: .venv-llm-eval, Python 3.12.3, OpenAI SDK 1.109.1. CPU 노트북 클라이언트, GPU/CUDA N/A.
- 코드: feat/llm-evaluation-foundation, 미커밋 변경 포함. 실행 commit/환경은 execution-summary.json, diff와 평가 모듈 snapshot은 아래 artifact에 보존.
- 데이터: dataset.v2.jsonl에서 coach-normal-02 선정. 관찰 결과가 있는 정상 C/A/V 사례. 두 번째 coach-normal-04는 첫 요청 차단으로 미실행.
- 조건: strict CoachingLLMOutput JSON Schema, require_parameters true, 자동 provider routing, temperature/reasoning 기본값, SDK 재시도 0, 명시 호출 1회, timeout 60초.
- 버전: report의 dataset/grader/config/schema 해시 및 prompt/Skill/criteria 버전 확인 가능. expected/annotation은 모델 입력에 넣지 않음.
- 실제 결과: HTTP 오류 latency 549.726ms. raw completion/generation/provider/usage/cost 없음. parse/schema/validator 및 품질 측정 불가. semantic/critical null.
- 실행 범위: sandbox 연결 오류 1회 후 외부 연결 허용 환경에서 실제 요청 1회. LLM 응답 재시도 없음. 전체 90건/Premium 호출 없음.
- artifact: local-results/openrouter-basic-20260918. execution-summary, smoke raw/error record, premium-failure-set, execute.py, working-tree.patch/source-snapshot.
- 재현: `.venv-llm-eval/bin/python -B local-results/openrouter-basic-20260918/execute.py smoke` (실 API 요청 발생). full phase는 smoke-gate passed=true일 때만 허용. 기존 결과를 보존하려면 별도 복사 경로로 실행.
- 판단: 계정/provider routing 인프라 실패는 Basic 품질 실패 및 Premium recovery 분모에 포함하지 않는다. 비용은 null이며 0으로 추정하지 않음.
- 다음: 계정 소유자가 ZDR/guardrail 설정과 해당 모델 provider 허용 정책을 확인. 현재 정책 유지/변경 여부 결정 후 smoke 재실행. 모델 ID/계정 정책 임의 변경하지 않음.
- Worklog: ../worklogs/2026-09-18_openrouter-basic-smoke.md
