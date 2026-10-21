# Worklog — 승인된 실제 OpenRouter Basic smoke

- 일시: 2026-09-18
- 작업자: Codex
- 요구: smoke 통과 후 Basic 3종 30건, Premium 미실행, 키 비공개

## 목적 / 작업 전 상태

전용 Python 3.12 환경과 평가 v2/runner를 사용해 실 API 저장을 검증한다. 기존 미커밋 변경을 보존했다.
필수 프로젝트 문서/evals README/실험 규칙을 확인했다.

## 수행 / 주요 판단

대표 case 02와 04를 선정했다. sandbox APIConnectionError 기록 후 허용된 외부 연결 실행으로 Qwen case 02 요청을 수행했다.
OpenRouter는 HTTP 404 및 계정 ZDR violation으로 endpoint 제외를 반환했다. 첫 요청 smoke gate를 false로 기록하고 case 04/전체 Basic/Premium을 실행하지 않았다.
계정 개인정보 정책을 바꾸거나 모델 ID를 대체하지 않았다. 미검토 semantic 및 critical 점수는 null이다.
인프라 실패를 Premium 품질 복구 set에서 제외하고 미실행 90건을 명시했다.

## 변경 파일 / Artifact

- docs/experiments/2026-09-18_openrouter-basic-smoke.md, 본 Worklog, docs/CURRENT_STATE.md
- local-results/openrouter-basic-20260918: 실행 스크립트/코드 snapshot/diff, sandbox 연결 오류, 실제 smoke 응답/error body, 버전 정보, 실행 요약, premium-failure-set. Git 무시 경로.

## 검증 / 문제

실제 SDK 오류 body에 zdr-violation-by-account 및 configure_url이 기록됐다. latency 549.726ms.
completion/generation/provider/token/cost는 없고 null 보존. schema/validator 미실행. 오류를 모델 품질 0점으로 해석하지 않는다.
키는 출력하지 않았다. 모델 응답이 없어 품질/성공당 비용/critical 자동 판정 수행 불가.

## 미확인 / 다음

Basic 전체 비교 및 Premium 복구는 미실행. 계정 소유자의 개인정보/guardrail 정책 확인과 결정 후 smoke를 재실행해야 한다.
