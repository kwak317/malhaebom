- [2026-10-09 전문가 규칙 검토 완료 확인](2026-10-09_expert-rule-review-confirmation.md)
- [2026-10-06 Skill 규칙 provenance · 전문가 검토 유보](2026-10-06_skill-rule-provenance.md)
# Worklogs

전체 기록은 [날짜별 인덱스](INDEX.md)에서 찾습니다. 아래 선택 목록은 주요 과거 작업을 설명하며 전체 목록을 대신하지 않습니다. 최신 완료 상태는 [CURRENT_STATE](../CURRENT_STATE.md)를 확인합니다.

- [2026-10-10 평가 리포트 날짜·버전·운영 근거 정리](2026-10-10_eval-report-version-scope.md)

- [2026-10-10 에이전트 리포트 운영 기준 최신화](2026-10-10_agent-report-production-update.md)

- [2026-10-09 배포 기준 Skill·met 조건 정합화 후보](2026-10-09_deployed-skill-met-alignment.md)

프로젝트의 의미 있는 작업 단위별 기록을 보관한다.

## 목적

Worklog는 다음 작업자가 코드와 문서의 변경 이유를 빠르게 복원할 수 있게 하는 실행 기록이다.

- 무엇을 하려고 했는가
- 작업 전에 어떤 상태였는가
- 무엇을 실제로 바꿨는가
- 어떻게 검증했는가
- 무엇이 아직 남아 있는가

## 파일명

권장 형식:

```text
YYYY-MM-DD_HHMM_<short-title>.md
```

예:

```text
[REDACTED].md
2026-09-18_1540_job-context-api.md
```

## 작성 원칙

- 실제 확인한 내용과 계획을 구분한다.
- 테스트하지 않았다면 테스트했다고 쓰지 않는다.
- 실패한 시도와 미해결 문제도 기록한다.
- 코드의 현재 상태가 바뀌었다면 `../CURRENT_STATE.md`도 갱신한다.
- 아키텍처가 바뀌었다면 `../ARCHITECTURE.md`도 갱신한다.
- 중요한 선택을 했다면 `../DECISIONS.md`에도 남긴다.

새 작업은 `TEMPLATE.md`를 복사해 시작한다.

## 필수 기록 항목

목적, 작업 전 상태, 수행한 작업, 주요 판단과 이유, 변경 파일, 검증 내용, 발견한 문제, 미확인 사항, 다음 작업을 모두 기록한다. [템플릿](TEMPLATE.md)을 사용한다.

## 기록 목록

- [2026-10-09 운영 HTTP 요청·Langfuse trace 연결](2026-10-09_request-trace-linkage-production.md)

- [2026-10-09 STT 파인튜닝 전·후 비교 리포트](2026-10-09_stt-finetuning-report.md)

- [2026-10-09 에이전트 구현·평가 리포트](2026-10-09_agent-report.md)
- [2026-10-08 D11 v5 신규 인젝션 02·03 추가 실호출 결과](2026-10-08_d11-v5-extra-retries.md)

- [2026-10-08 D11 신규 인젝션 3건 실측 및 v5 제한 재시도](2026-10-08_d11-injection-retry-results.md)

- [2026-10-08 D11 신규 인젝션 3건 사람 검토 패킷 인계](2026-10-08_d11-review-handoff.md)

- [2026-10-08 D10 운영 Prompt @4·Langfuse 출력 검증과 접근 한계](2026-10-08_d10-production-readonly-evidence.md)

- [2026-10-08 D12 평가 보고서·체크리스트·제출 증거 정합성](2026-10-08_d12-evaluation-submission-alignment.md)

- [2026-10-07 UI 테마·코칭 화면 새로고침 설계](2026-10-07_ui-theme-coaching-refresh-design.md)
- [2026-10-06 D10 운영 증거 수집 runbook](2026-10-06_1515_d10-evidence-capture-runbook.md)
- [2026-10-06 D11 신규 인젝션 사람 검토 preflight](2026-10-06_1500_d11-human-review-preflight.md)
- [2026-10-06 Windows job-source E2E token-file permission](2026-10-06_1441_windows-token-file-permission.md)

- [2026-10-06 운영 관측·사람 평가 증거 연결](2026-10-06_observability-human-evidence.md)

- [2026-10-05 I/D 판단 경계 사례 9·10 리뷰 PR](2026-10-05_skill-id-examples-review-pr.md)

- [2026-10-06 공고 원문 분석 증거를 보존 운영 로그 기준으로 정리](2026-10-06_job-source-production-evidence-pr.md)

- [2026-10-02 D10 관측 개선 가설과 D11 baseline 오프라인 사전점검](2026-10-02_d10-d11-eval-preflight.md)
- [2026-10-02 평가 증거·누락 항목 교차검증](2026-10-02_eval-evidence-gap-audit.md)
- [2026-10-02 코칭 Prompt·Skill 실행 버전 정합성](2026-10-02_coaching-version-provenance.md)
- [2026-10-02 Gemini v5 자동 불일치 사람 검토 양식](2026-10-02_1140_gemini-v5-human-review-prep.md)
- [2026-10-02 STT 실험 근거와 체크리스트 상태 재정렬](2026-10-02_stt-checklist-evidence-refresh.md)
- [2026-10-02 3조 최신 강사 피드백 후속 검증 체크](2026-10-02_team3-latest-instructor-feedback.md)
- [2026-10-02 Gemini v5 4,096-token 출력 계약 재검증](2026-10-02_1045_gemini-v5-4096-contract-recheck.md)
- [2026-10-02 최신 영문 v5 Prompt 재측정 및 EVAL_REPORT 정리](2026-10-02_latest-english-v5-eval-report.md)
- [2026-10-02 영문 v4 팀 품질 검토 취합 게시](2026-10-02_coaching-v4-team-quality-review.md)

- [2026-10-01 유지관리 문서 참조 및 링크 검사](2026-10-01_1500_repo-doc-reference-guard.md)

- [2026-10-01 로그인 사용자 공고 원문 분석 E2E](2026-10-01_1400_job-source-authenticated-e2e.md)

- [2026-10-01 강사 별도 컨펌 항목 체크 종료](2026-10-01_instructor-confirmed-checklist-items.md)

- [2026-10-01 STT 파인튜닝 계보 문서화](2026-10-01_1109_stt-finetuning-lineage.md)

- [2026-10-01 체크포인트 정합성 및 D7 한 장 정리](2026-10-01_1035_checkpoint-cleanup.md)

- [2026-10-01 MCP 오류 프런트엔드 타입 계약 정합성](2026-10-01_1030_mcp-error-frontend-type.md)
- [2026-10-01 D7 체크포인트 근거 최신화](2026-10-01_d7-checkpoint-refresh.md)

- [2026-09-30 코칭 Before / After 평가 artifact 고정](2026-09-30_1700_coaching-before-after-artifact.md)

- [2026-09-30 제품 테스트 CI 추가](2026-09-30_1617_product-test-ci.md)
- [2026-10-01 백엔드 CI 중복 실행 제거](2026-10-01_1510_ci-pytest-single-run.md)

- [2026-09-30 3조 강사 피드백 보완 체크 추가](2026-09-30_instructor-feedback-checklist.md)

- [2026-09-30 D5 기술 작업 종료 및 운영 항목 분리](2026-09-30_d5-checkpoint-close.md)

- [2026-09-30 D4 평가셋 30건 사람 검토](2026-09-30_d4-human-review.md)

- [2026-09-30 Checkpoint schedule 기준 문서 재구성](2026-09-30_checkpoint-schedule-rewrite.md)

- [2026-09-29 D6 Agent live E2E runner 자동화](2026-09-29_1723_d6-agent-e2e-runner.md)
- [2026-09-29 D6 Agent 실제 사용자 3종 E2E 검증](2026-09-29_1632_d6-agent-live-e2e.md)
- [2026-09-29 인증 사용자 Langfuse E2E 및 실패/retry 검증](2026-09-29_1430_langfuse-authenticated-e2e.md)
- [2026-09-29 D6 체크포인트 상태 점검](2026-09-29_1415_d6-checkpoint-status.md)

- [2026-09-29 체크포인트 작업티켓 최신화](2026-09-29_0032_checkpoint-status-refresh.md)
- [2026-09-28 Analysis E2E benchmark 실행](2026-09-28_analysis-e2e-benchmark.md)

- [2026-09-28 STT service-runtime parity](2026-09-28_1412_stt-runtime-parity.md)

- [2026-09-28 STT 동적 initial prompt 연동](2026-09-28_1030_stt-dynamic-initial-prompt.md)
- [2026-09-28 STT prompt / hotwords A/B](2026-09-28_1000_stt-prompt-hotwords-ab-prep.md)
- [2026-09-28 STT devset provenance 유틸](2026-09-28_1135_stt-devset-provenance.md)
- [2026-09-28 STT 실사용 모델 × beam 비교](2026-09-28_0932_stt-real-user-matrix-prep.md)
- [2026-09-28 STT 실사용 평가 무결성 유틸 분리](2026-09-28_1110_stt-eval-integrity-utils.md)
- [2026-09-28 STT 실사용 devset 준비](2026-09-28_0905_stt-real-user-devset-prep.md)

- [2026-09-27 STT 실사용 녹음 평가 문서화](2026-09-27_1706_stt-real-user-eval.md)

- [2026-09-23 Terra 우선 Gemini Fallback 평가 실행](2026-09-23_0030_terra-gemini-fallback-test.md)
- [2026-09-23 GitHub README 출력 계약 강제](2026-09-23_0015_github-output-contract-enforcement.md)

- [2026-09-23 GPT-6 Luna / Sol 평가 실행 준비](2026-09-23_1130_gpt6-evaluation-prep.md)
- [2026-09-23 문서 정합성 정리](2026-09-23_1020_document-consistency-cleanup.md)

- [2026-09-23 제품 문제정의·차별화 전략 문서화](2026-09-23_0930_product-definition-and-differentiation.md)
- [2026-09-22 STT persona + AI Hub 71592 continuation](2026-09-22_stt-persona-71592-continuation.md)
- [2026-09-22 GitHub 공고 핏 모델 비교 출력 개선](2026-09-22_1745_github-job-fit-readable-output.md)
- [2026-09-22 GitHub README URL 테스트 경로 수정](2026-09-22_1730_github-readme-url-test-fix.md)
- [2026-09-22 GitHub 기술 증거 기반 공고 핏 진단 Spec](2026-09-22_1709_github-evidence-job-fit-spec.md)

- [2026-09-21 STT clean continuation overnight prep]([REDACTED].md)

- [2026-09-16 문서 bootstrap](2026-09-16_docs-bootstrap.md)

- [2026-09-16 수업 지식·공식 요구사항 통합]([REDACTED].md)

- [2026-09-16 프로젝트 운영 규칙](2026-09-16_operating-rules.md)
- [2026-09-18 STT/TTS Python 환경 재구성](2026-09-18_python-environments.md)
- [2026-09-19 STT fine-tuning preflight]([REDACTED].md)
- [2026-09-18 TTS 공개 모델 배포 경로]([REDACTED].md)
- [2026-09-18 STT 공개 모델 배포 경로]([REDACTED].md)
- [2026-09-18 AI Hub STT 119 다운로드·재구성 정리]([REDACTED].md)
- [2026-09-19 STT retrain setup]([REDACTED].md)
- [2026-09-20 overnight long-job runner]([REDACTED].md)
- [2026-09-21 compare_attempts MCP 구현](2026-09-21_1251_compare-attempts-mcp.md)

- [2026-10-04 도메인 확장 제외 문구 정리](2026-10-04_domain-expansion-scope-cleanup.md)

- [2026-10-06 도메인 확장 범위 문서 재점검](2026-10-06_domain-scope-reaudit.md)

- [2026-10-06 코칭 기본 Prompt를 배포 v4로 복원](2026-10-06_default-coaching-prompt-v4.md)

- [2026-10-06 최신 운영 배포 반복 평가·raw 공개 PR](2026-10-06_coaching-raw-repeat3-pr.md)

- [2026-10-06 README 배포 주소 추가](2026-10-06_readme-deployment-links.md)

- [2026-10-06 보강 후보 v5 Langfuse·GitHub 등록](2026-10-06_coaching-v5-reinforced-registration.md)

- [2026-10-06 코칭 판정 기준 단일 기준원 점검](2026-10-06_coaching-rule-source-audit.md)
- [2026-10-06 Prompt 입력·보안 경계 정적 점검](2026-10-06_prompt-input-security-audit.md)

- [2026-10-06 System Prompt 역할 단위 섹션 정리](2026-10-06_system-prompt-section-contract.md)

- [2026-10-06 D11 신규 인젝션 3건 후보](2026-10-06_d11-injection-candidates.md)

- [2026-10-06 공개 배포 주소 재검증과 체크포인트 정합성](2026-10-06_1000_deployment-url-reverification.md)

- [2026-10-06 공개 배포 smoke 자동화](2026-10-06_1015_deployment-smoke-tool.md)

- [2026-10-06 D11 운영 baseline과 preflight 정합성](2026-10-06_1030_d11-baseline-alignment.md)

- [2026-10-06 최종 제출 증거 인덱스](2026-10-06_1045_submission-evidence-index.md)

- [2026-10-06 현재 기본 Prompt + Skill 중복·충돌 점검](2026-10-06_current-prompt-skill-conflict-audit.md)

- [2026-10-09 운영 동기화 1: audit](2026-10-09_production-sync-audit.md)

- [2026-10-09 운영 동기화 2: selection](2026-10-09_production-sync-selection.md)

- [2026-10-09 운영 동기화 3: freechat](2026-10-09_production-sync-freechat.md)

- [2026-10-09 운영 동기화 4: conversation](2026-10-09_production-sync-conversation.md)

- [2026-10-09 운영 동기화 5: transport](2026-10-09_production-sync-transport.md)

- [2026-10-09 운영 동기화 6: normalization](2026-10-09_production-sync-normalization.md)

- [2026-10-09 운영 동기화 7: runtime](2026-10-09_production-sync-runtime.md)

- [2026-10-09 운영 동기화 8: chat-ui](2026-10-09_production-sync-chat-ui.md)

- [2026-10-09 운영 동기화 9: loading-ui](2026-10-09_production-sync-loading-ui.md)

- [2026-10-09 운영 동기화 10: practice-ui](2026-10-09_production-sync-practice-ui.md)

- [2026-10-09 운영 동기화 11: styles](2026-10-09_production-sync-styles.md)

- [2026-10-09 전체 백엔드 재검증](2026-10-09_production-sync-verification-followup.md)
