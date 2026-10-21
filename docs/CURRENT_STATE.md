# Current State

## 2026-10-11 이력서 PDF 가져오기 500 수정

`extract_resume_pages`가 폼 가져오기에서 전달하는 `redact_private=False`를 지원하도록
수정했다. 기본 이력서 분석은 개인정보 가림을 유지한다. 실제 PDF 추출 및 인증·동의·
파일 검증·CORS 관련 25 tests 및 전체 backend 848 tests 통과(모델 대역 사용).
GitHub Actions는 계정 결제/사용 한도 문제로 실행되지 않아 로컬 검증했다. 운영 배포 결과는 별도 검증한다.
[Worklog](worklogs/2026-10-11_resume-import-keyword-fix.md).

> 운영 제품 기준(2026-10-10): main e6ecc4b / Vercel dpl_A6EgFiF3ABvaGNm8Q41QA2ed6A2P / Cloud Run malhaebom-mk2-main-sync-final-1010. 아래 날짜별 항목은 당시 기록이며 과거의 미배포·기본값 설명을 현재 상태로 해석하지 않습니다. [문서 입구](README.md), [작업 이력](worklogs/INDEX.md), [평가 안내](../evals/README.md).


## 2026-10-10 로컬 CPU 재현과 저장소 안내 정리

로컬 Compose만 CPU 전용 이미지로 분리하고 Torch/TorchAudio 2.8.0·PyAV 16.1.0을 고정했다. 운영 Dockerfile·배포 설정·STT 모델은 유지했다. 새 clone 후보는 독립 빌드 캐시 환경에서 6분 34.86초에 웹/API healthy, 실제 소개→연습 로그인 안내 표시를 확인했다. 같은 공개 모델 캐시를 사용한 합성 WAV STT/VAD를 확인했으며 최초 모델 전체 다운로드·인증/DB/코칭 E2E는 별도다. README/문서/Worklog/평가 안내를 정리하고 미사용 소개 WebP 4개를 원본 보관 이동했다. [Spec](specs/local-cpu-reproduction.md), [증거](evidence/local-cpu-reproduction-20261010.md), [Worklog](worklogs/2026-10-10_local-cpu-reproduction.md).

## 2026-10-10 소개 기능 설명과 운영 미리보기 갱신

누락된 NCS/자료 연결·이력서 PDF 분석·공고 추천/검색·직접 질문·표준어 변환·자유채팅/경험 반영·이력서 초안/PDF·기록 조회/삭제 설명을 보강했다. 미리보기는 10/10 실제 운영 NCS·이력서 제출 화면 2개로 교체했다. 정적 검사/production build, 1280px/375px 표시 검증 통과. [Spec](specs/showcase-current-features.md), [캡처 manifest](showcase/production-preview-manifest-20261010.json), [Worklog](worklogs/2026-10-10_showcase-current-features.md).

## 2026-10-10 운영 소개페이지 및 main 실행 소스 동기화

`https://malhaebom.xyz/`와 `https://www.malhaebom.xyz/` 첫 화면을 소개페이지로 배포했다. 연습 시작은 `/app/practice`, 서비스 홈은 `/app/`로 연결된다. 기존 운영의 이력서/PDF·채팅/페이지 탐색 기능을 이관하고 main의 보안·평가 자료는 보존했다. 최종 제품 코드 main `fef359c4a243ba6935762cabd2f0d65fcec19119`, Vercel `dpl_DzgZXQjBThyCAeweLygj13wQQ5dr`, Cloud Run `malhaebom-mk2-main-sync-final-1010`이다.

양쪽 도메인 6개 HTML 경로와 JS/CSS 바이트 일치, 기존 로그인 상태 브라우저의 소개→채팅 및 서비스 홈→소개 복귀를 확인했다. backend image 내 main 추적 runtime 152파일 SHA256 일치, 환경/secret 참조·리소스·인증 설정 보존, health 200·이력서 API 비인증 401을 확인했다. frontend 279 tests/build, 기존 backend 832 tests + 추가 회귀 11 tests 통과. 신규 Google OAuth 완료 및 실녹음/STT/코칭/DB 전체 E2E는 재실행하지 않았다. GitHub Actions는 billing 제한으로 시작되지 않아 로컬 검증을 사용했다. [운영 증거](evidence/serving-source-main-sync-20261010.json), [Worklog](worklogs/2026-10-10_serving-source-main-sync.md).

## 2026-10-10 에이전트 리포트 운영 기준 최신화

[에이전트 리포트](AGENT_REPORT.md)를 현재 운영 `malhaebom-mk2-custom-question-1010`(트래픽 100%) 및 배포사이트와 대조했다. 준비용 PDF 분석과 비교 이후 이력서 정보 가져오기·문장 다듬기·문서/PDF 흐름, 직접 입력 질문 코칭, 참고정보·재선택·재답변 기능과 병합 상태를 구분했다. 사이트·health·OpenAPI 200과 배포 JS/API를 확인했으며 새 LLM 평가·개인 PDF 제출·DB 저장·전체 E2E는 실행하지 않았다. 운영 기능 전체를 main으로 이식한 변경은 아니다. [증거](evidence/agent-report-20261010.json), [Worklog](worklogs/2026-10-10_agent-report-production-update.md).

## 2026-10-09 운영 소스 GitHub 동기화 후보

운영 이미지와 Vercel 원본·Langfuse를 읽어 활성 기능의 리뷰 후보를 준비했다. 운영 설정·DB·라벨·트래픽 변경과 머지는 하지 않는다. GitHub의 인증/만료/버전 provenance 개선은 보존한다. [비교 보고서](evidence/production-source-sync-2026-10-09.md)를 따른다.

## 2026-10-09 배포 기준 Skill·met 조건 정합화 후보

운영 `reference-finish-1009-verified`와 Langfuse reinforced v5 @4의 판정표가 Skill의 정성적 결과 인정 조건과 달랐다. 운영 본문에서 도메인 규칙을 제거한 명시 선택 후보 `coaching-v5.4-skill-met-aligned`, Skill v6.2 및 유형 문서/JSON 6개 기준 × 4개 상태 정합성 검사를 추가했다. 관련 100 tests 통과. 운영 배포·원격 라벨·기존 기본값은 변경하지 않았다. 실제 LLM 품질 개선과 D10/D11 완료는 주장하지 않는다. [Spec](specs/deployed-skill-met-alignment.md), [Worklog](worklogs/2026-10-09_deployed-skill-met-alignment.md).

## 2026-10-09 운영 요청과 Langfuse trace 직접 연결

운영 revision `malhaebom-mk2-request-trace-linkage-1009`에 HTTP trace 연결을 배포했다. 실제 사이트 채팅 200과 브라우저 입력 오류 422에서 응답 X-Trace-Id·Langfuse trace ID·Cloud Run 로그 ID가 일치했다. OAuth 로그인 화면·마이크/STT·사람 품질 평가는 별도 미확인이다. [증거](evidence/request-trace-linkage-2026-10-09.md), [Worklog](worklogs/2026-10-09_request-trace-linkage-production.md).

## 2026-10-09 STT 파인튜닝 전·후 비교 리포트

기존 [STT 계보 문서](stt-finetuning-lineage.md)를 전·후 비교 리포트로 보강했다. Drive 가이드·README·체크섬 게시 내용을 열람하고 첨부 문서와 저장소 실험을 대조했다. 24건·기술 질문 지표는 발화형 정규화로 명시하며, raw WER·기존 도메인 회귀도 함께 보고한다. 새 학습·추론·ZIP 다운로드 검증·운영 모델 변경은 수행하지 않았다. [Worklog](worklogs/2026-10-09_stt-finetuning-report.md).

## 2026-10-09 에이전트 구현·평가 리포트

[에이전트 리포트](AGENT_REPORT.md)에 Prompt·Skill·MCP·서버 책임, 과거 코칭/자유채팅 평가와 운영 HTTP 연결 증거를 종합했다. 현재 Cloud Run revision·트래픽을 읽기 전용 확인했으며 새 평가·배포·Prompt/Skill 변경은 수행하지 않았다. 계약·오류 미검출·기능 성공·사람 품질·전체 E2E는 별도 지표로 유지한다. [Worklog](worklogs/2026-10-09_agent-report.md).
## 2026-10-08 D11 신규 인젝션 3건 Prompt 실측 결과 (단일 검토자 잠정)

- 기존 `local-results/d11-human-review-2026-10-07/human-review.user-filled.json`의 사용자 3건 검토·근거를 사용해 동일 Gemini 3.5 Flash-Lite·Skill·3개 합성 입력에서 Prompt v4/v5를 비교했다. 사람 검토 기록은 10/7에 존재했으나 **독립 검토자 요건은 미충족**이다.
- v4는 재시도 포함 계약·기대 C/A/V·intent 판정 3/3, v5는 추가 재시도까지 포함하면 **계약 3/3, 기대 판정 2/3**이다. v5 인젝션 02의 `own_action=met`은 기대 `partial`과 불일치. 최초 호출만의 v5 계약 1/3과 재시도 포함 3/3을 구분한다. [실험 기록](experiments/2026-10-08_d11-injection-prompt-ab-provisional.md), [작업 기록](worklogs/2026-10-08_d11-v5-extra-retries.md).
- 추가 개선 없이 관측 결과와 미검증 한계만 남긴다. 독립 확인·공식 Dataset 승격·보안 효과 확정·운영 E2E는 수행하지 않았다. 아래의 패킷 인계/미측정 언급은 **실호출 이전 시점의 이력**이다.

## 2026-10-08 D11 독립 사람 검토 패킷 인계

- 기존 신규 인젝션 3건 생성기에 기본 출력 경로를 추가하고 `local-results/d11-injection-review-20261008/`에 검토 원문·빈 판정 양식을 생성했다. 기존 생성기 테스트 2건 통과, 유료 provider 호출 0회. [인계 문서](evidence/d11-human-review-handoff-2026-10-08.md), [Worklog](worklogs/2026-10-08_d11-review-handoff.md).
- 기존 Gemini v5 자동 불일치 7건의 로컬 `comparison.json` 원본은 확인되지 않아 모델 응답 검토자료 재생성과 사람 평가는 보류했다. 사람 독립 판정·평가셋 승격·동일 조건 방어 전후 측정은 모두 미완료.

## 2026-10-08 D10 Langfuse 관리형 Prompt 및 출력 계약 관측

- 사용자 제공 Langfuse Cloud 캡처에서 `malhaebom-coaching-v5-reinforced-verification`의 **#4 `production`·`latest`** 및 같은 버전 `Linked Generations`의 **12:38:46 코칭 trace ID 일치**를 확인했다. `coaching.provider`는 `...reinforced-verification@4`, Gemini 3.5 Flash-Lite, HTTP 200, 약 8.19초, $0.006809; 동일 trace의 `coaching.output_validation`은 `valid=true`, `error_count=0`이었다. provider·validation에 `interview-coach-v6`이 **기록**되지만 실제 Skill 번들 로드는 별도다.
- 10/8 공개 Frontend GET 200. 로컬 GCP 계정으로는 운영 Cloud Run 서비스의 revision을 확인할 수 없었고, 두 Cloud Run health 주소의 5초 timeout은 **장애 확정 증거가 아니다**. 운영 배포 revision/Skill 실제 번들/DB/PlayMCP 동일 요청 연계 및 Prompt release/rollback은 미확정·미완료로 둔다. [D10 비식별 Worklog](worklogs/2026-10-08_d10-production-readonly-evidence.md). 운영 변경·추가 LLM 호출 없음.

## 2026-10-06 재답변 composer

1차 코칭 뒤 보내기 옆 재답변하기로 녹음·WAV 패널을 연다. 준비 대화 API는 선행 #194·#195와 함께 사용하며, 연결 실패는 표시하되 녹음 세션 생성은 유지한다. [Worklog](worklogs/2026-10-06_coaching-composer-reanswer.md).
## 2026-10-06 준비 대화 API·DB 연결

인증된 준비/1차 코칭 대화와 같은 연습의 추가 경력 저장·참고 전달 경로를 구현했다. 서버만 쓰는 초안, 명시적 동의, 요청 ID와 CAS 검증을 적용한다. 기존 답변·점수는 불변이다. 정책/JSON/runtime/API 등 82 tests 통과. 운영 검증은 배포 후 별도이며 마이크/STT 전체 E2E를 주장하지 않는다. [Spec](specs/preparation-conversation-runtime.md), [Worklog](worklogs/2026-10-06_preparation-conversation-runtime.md).
## 2026-10-06 준비 대화 Prompt·Skill v3.1

NCS·README·이력서·1차 코칭 질문과 채팅 경력 정리 후보를 별도 추가했다. 기존 코칭 평가 기본값은 유지한다. 로컬 12×3 자동 평가 증거와 제품 API 연결은 별도 PR이다. [Worklog](worklogs/2026-10-06_preparation-prompt-skill-review.md).


## 2026-10-06 현재 v5 Prompt + Skill 중복·충돌 점검

- 현재 작업·평가 기준 `coaching-v5-skill-owned`와 현재 GitHub Skill을 canonical builder로 합성해 점검했다. v5 Prompt는 도메인 판정표를 소유하지 않고, intent/C/A/V 및 result_verification 규칙은 Skill에서만 한 번 포함된다.
- 따라서 현재 v5 조합에서는 도메인 규칙 중복·충돌이 확인되지 않았다. archived v4를 현재 Prompt로 간주했던 초기 점검은 버전 층위를 섞은 것이어서 정정했다.
- local fallback/default selector와 마지막 저장소 운영 증거의 v4, 별도 Langfuse v5 candidate는 현재 v5 작업 기준과 구분한다. 실제 live production이 v5인지 여부는 D10 운영 증거에서 별도로 확인한다. [증거](evidence/current-prompt-skill-conflict-audit-2026-10-06.md), [Worklog](worklogs/2026-10-06_current-prompt-skill-conflict-audit.md).

## 2026-10-06 Skill 규칙 1개 A/B smoke

- `coach-boundary-19`에서 Dataset v2·`coaching-v5-skill-owned` Prompt·Gemini 3.5 Flash-Lite·grader·generation 설정을 고정하고 off-topic ↔ C/A/V 독립 판정 **Skill 규칙 한 줄만** 바꿔 baseline/candidate 각 1회 실호출했다.
- 계약은 양쪽 100%였지만 target hit는 baseline 2/3 → candidate 1/3, 전체 label accuracy는 75% → 50%로 하락했다. 특히 `own_action`이 met → partial로 회귀해 자동 gate는 **DISCARD_CANDIDATE**를 냈다.
- smoke에서 target 회귀가 확인돼 전체 30건 × 2회 확대 실행은 gate 정책대로 중단했다. 사람 최종 확인 전이므로 체크리스트는 아직 부분완료로 유지한다. [Worklog](worklogs/2026-10-06_single-skill-rule-offtopic-cav.md).

## 2026-10-06 D10 운영 증거 수집 runbook

- production trace·Prompt release/rollback·PlayMCP 동일 요청 E2E·제출용 Langfuse 캡처를 같은 실행 단위로 수집하는 절차를 문서화했다. runbook은 권한·비식별 테스트 계정·배포 창이 필요한 운영 작업을 대신 실행하지 않는다.
- D10 상태는 그대로 부분완료다. 실제 revision·trace·DB·Prompt/Skill 값의 연결과 release/rollback 실증 전에는 완료로 바꾸지 않는다. [Runbook](runbooks/d10-production-evidence-capture.md), [Worklog](worklogs/2026-10-06_1515_d10-evidence-capture-runbook.md).
## 2026-10-06 D11 신규 인젝션 사람 검토 packet

- `evals/build_d11_injection_human_review.py`는 후보 3건을 바탕으로 git-ignored `local-results/`에 사람 검토용 Markdown과 빈 template을 생성한다. 검토자·일시·입력 처리·독립 근거·최종 판정은 사람이 채워야 하며, 이 도구는 provider 호출·공식 Dataset 갱신·유료 평가를 하지 않는다.
- 후보의 LLM 초안 provenance가 남아 있으므로, packet 생성만으로 공식 D11 신규 3건 또는 before/after 측정을 완료로 바꾸지 않는다. [Spec](specs/d11-human-review-preflight.md), [Worklog](worklogs/2026-10-06_1500_d11-human-review-preflight.md).
## 2026-10-06 Windows job-source E2E token-file 경계

- `.env.job-source-e2e` fallback은 POSIX mode를 신뢰할 수 없는 Windows에서 사용하지 않고, `JOB_SOURCE_E2E_ACCESS_TOKEN` 또는 `D6_ACCESS_TOKEN` 환경변수를 요구한다. POSIX에서는 기존 `chmod 600` 검사와 파일 fallback을 유지한다.
- Windows 전용 안내와 POSIX 전용 권한 검사를 각각 회귀 테스트로 분리했다. 이는 live E2E 실행이나 토큰을 제공하지 않는다. [Worklog](worklogs/2026-10-06_1441_windows-token-file-permission.md).

## 2026-10-06 System Prompt 역할 단위 섹션 정리

- mutable LLM system Prompt를 `[역할] → [입력 경계] → [출력 계약] → [안전 경계]` 순서로 통일했다. README 분석·공고 요구사항 분석·비교 후 면접 대화·Skill-owned 코칭 후보·채용 검색 의도·질문 rubric 생성/평가/예시가 대상이다.
- 현재 배포 v4 `prompts/coaching.md`는 10/6 반복평가·Prompt hash 재현과 연결된 frozen snapshot이라 수정하지 않았다. 따라서 전체 호출 구조 통일은 아직 **부분완료**이며 다음 production 후보를 Skill-owned 4섹션 구조로 재평가·승격해야 완료된다.
- 구조 회귀 테스트는 mutable Prompt의 필수 4섹션과 frozen v4 예외를 함께 고정한다. [Spec](specs/system-prompt-section-contract.md), [증거](evidence/system-prompt-section-audit-2026-10-06.md), [Worklog](worklogs/2026-10-06_system-prompt-section-contract.md).

## 2026-10-06 Skill 규칙 provenance · 전문가 검토 유보

- `skills/interview-coach/rule-provenance.json`에 canonical criterion **33개 전부**의 도입 이유·규칙 출처·전문가 검토 상태를 ID별로 연결했다.
- 2026-10-09 사용자가 김창민(IT 업계 면접관 경험 있음)의 33개 전체 검토 완료를 확인하여 `reviewed / 김창민 검토 완료`로 기록했다. 이름·경험·완료 여부는 사용자 제공 정보이며 별도 검토 원문은 첨부되지 않았다. [Worklog](worklogs/2026-10-09_expert-rule-review-confirmation.md).
- provenance는 추적 메타데이터이며 모델 system prompt에는 합성하지 않는다. coverage/version/source/review-state 회귀 테스트를 추가했다. [증거 문서](evidence/skill-rule-provenance-2026-10-06.md), [Worklog](worklogs/2026-10-06_skill-rule-provenance.md).

## 2026-10-06 코칭 판정 기준 단일 기준원 고정

- 코칭 판정의 canonical source를 `load_skill_bundle()`이 조립하는 **versioned Skill bundle 하나**로 명시했다. `criteria.json`은 ID·버전·검토 상태·기계 판독 계약, 질문 유형 문서는 경계 판정, `SKILL.md`는 공통 절차와 입력 신뢰 경계를 소유한다.
- 현재 운영 템플릿(`coaching.md`, `coaching-v5-skill-owned`)이 Boundary table·700ms 사례·과거 결과 검증 marker를 직접 소유하지 않는 회귀 검사를 추가했다. 배포 v4와 과거 실험 Prompt는 hash 재현용 비canonical snapshot으로 보존한다.
- 등록된 reinforced v5 candidate는 배포 v4 기반 판정표를 포함한 실험 snapshot이라 **그대로 production 승격하지 않는다.** 다음 승격 후보는 Skill-owned 구조로 이관 후 재평가한다. [점검 문서](evidence/coaching-rule-source-audit-2026-10-06.md).

## 2026-10-06 D11 신규 인젝션 3건 후보

- 기존 30건의 `coach-failure-23/28/29`와 겹치지 않는 신규 인젝션 3건 후보를 `evals/d11_injection_candidates.jsonl`에 별도 고정했다.
- 사용자가 A 승인 / B `own_action=partial` / C 승인으로 제안 판정을 확인했다. 다만 입력과 정답이 모두 LLM 초안에서 시작했으므로 기존 D11 사전점검 정책상 **공식 신규 3건으로 아직 계산하지 않는다.** 독립 사람이 입력 문장을 직접 작성·수정하거나 별도 검토자가 입력·정답·근거를 다시 확정해야 한다. [증거 문서](evidence/d11-injection-candidates-2026-10-06.md), [Worklog](worklogs/2026-10-06_d11-injection-candidates.md).
- 후보 3건은 Pydantic 평가셋 계약을 통과했고 canonical Dataset v2 30건과 ID가 겹치지 않는다. provider 호출·유료 평가·before/after 측정은 수행하지 않았다.

## 2026-10-06 배포 v4 기반 보강 후보 v5 등록

- 어제 보강 후보를 `coaching-v5-reinforced-verification`으로 별도 등록했다. Langfuse는 `malhaebom-coaching-v5-reinforced-verification`의 `candidate` 라벨이며 숫자 버전·본문 해시는 [등록 manifest](evidence/coaching-v5-reinforced-registration-2026-10-06.json)에 고정했다.
- v4 기본값·기존 `coaching-v5-skill-owned`·Skill·모델·운영 v4 production 라벨을 유지한다. 새 LLM/인젝션 평가·운영 배포·GitHub 병합은 수행하지 않았다. 어제 점수는 당시 Skill v6와 출력 상한 4096 조건의 과거 증거다. [Spec](specs/coaching-v5-reinforced-registration.md), [Worklog](worklogs/2026-10-06_coaching-v5-reinforced-registration.md).

## 2026-10-06 공개 배포 주소 재검증

- README에 기록된 Frontend `https://malhaebom.xyz`와 Cloud Run API `https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app`를 외부에서 읽기 전용으로 재검증했다. Frontend와 `/health`는 HTTP 200이고 health 응답은 `{"status":"ok"}`였다.
- Frontend Origin에서 API로 보내는 CORS preflight도 HTTP 200이며 `Authorization` 요청 헤더와 `GET, POST, DELETE` 메서드를 허용했다. 공개 접속과 CORS 확인만으로 로그인 사용자 E2E, 코칭 품질, production Langfuse trace 또는 Prompt rollback을 완료로 간주하지 않는다.
- [README 배포 주소](../README.md#배포-주소), [Worklog](worklogs/2026-10-06_1000_deployment-url-reverification.md).

## 2026-10-06 공개 배포 smoke 자동화

- 공개 Frontend GET, Cloud Run `/health` JSON, Frontend Origin CORS를 비밀값 없이 한 명령으로 확인하는 `scripts/check_deployment_smoke.py`를 추가했다. 로컬 HTTP 서버를 사용한 성공·비정상 health 회귀 테스트와 실제 운영 주소 통합 실행이 통과했다.
- Cloud Run이 반환하는 lowercase CORS 헤더를 실제 통합 실행에서 발견해 헤더 이름을 대소문자와 무관하게 처리하도록 고정했다. 이 검사는 공개 네트워크 경계만 다루며 로그인 E2E·Langfuse·코칭 품질을 대신하지 않는다. [Worklog](worklogs/2026-10-06_1015_deployment-smoke-tool.md).

## 2026-10-06 D11 운영 baseline 정합성 갱신

- 이미 저장된 운영 이미지 30건×3회 결과를 D11 baseline 근거로 연결했다. 계약 90/90, 자동 전체 통과 57/90이며 회차별 boundary 통과는 모두 4/10으로 가장 약했다. 새 출력 사람 평가는 미수행이므로 자동 품질 수치를 사람 품질 점수로 표현하지 않는다.
- `evals/prepare_d11_baseline.py`의 이전 v5 하드코딩을 제거하고 현재 코드의 `DEFAULT_COACHING_PROMPT_VERSION`을 사용하게 했다. 생성한 오프라인 manifest는 v4 `coaching-user-supplied-v4-verification`, Skill v6.1, Dataset v2 30건을 고정했고 model calls 0·paid run 미승인을 유지했다.
- 신규 인젝션 3건과 단일 변경 전후 실험은 여전히 미완료다. [Worklog](worklogs/2026-10-06_1030_d11-baseline-alignment.md).

## 2026-10-06 최종 제출 증거 인덱스

- 저장소의 URL·문서·미디어를 대조해 [제출 증거 인덱스](SUBMISSION_EVIDENCE.md)를 만들었다. 서비스·API·health·재현 절차·Skill/MCP는 연결했으며, `EVAL_REPORT.md`는 추가 평가가 남아 일부 완료로 기록했다.
- 추적된 Langfuse 이미지는 홈 대시보드 1장뿐이고 trace 상세 필수 캡처 3장을 충족하지 않는다. 정상·실패 데모 영상, 별도 소개 페이지 URL, 발표 PDF도 저장소에서 확인되지 않아 미완료로 유지했다. [Worklog](worklogs/2026-10-06_1045_submission-evidence-index.md).

## 2026-10-06 운영 관측·사람 평가 증거 연결

- Langfuse의 과거 trace 2개·관측 4개를 서버에서 읽기 전용 재확인하고 실제 코칭 응답 사람 평가 기록을 연결했다. 인증 실패 직접 연결과 코칭 성공 시간 대조, 과거 평가와 최신 버전 미검증을 구분한다. [증거 문서](evidence/observability-human-evaluation-2026-10-06.md). 새 E2E·배포는 수행하지 않았다.

## 2026-10-06 배포 v4로 코칭 기본 Prompt 복원

- 환경변수 미설정·공백의 기본 선택과 `.env.example`을 `coaching-user-supplied-v4-verification`으로 맞췄다. v4 본문도 불변 배포 archive와 동일하게 복원했으며, 명시적 v5 선택은 유지한다.
- 현재 GitHub Skill·모델·외부 설정은 변경하지 않았다. PR 병합과 운영 배포는 별도이며 LLM 품질 개선을 주장하지 않는다. [Spec](specs/default-coaching-prompt-v4.md), [Worklog](worklogs/2026-10-06_default-coaching-prompt-v4.md).

## 2026-10-05 I/D 판단 경계 사례 9·10 PR 준비

GitHub main의 사례 1~8에 로컬의 개인 행동/선택 이유 및 관찰 신호/원인 추론 사례 9·10과 관련 I/D 설명을 추가했다. 관련 로더·Prompt 검사 28개 통과. 실제 LLM 재평가·로그인 E2E는 미검증이며 이번 작업은 리뷰 PR 준비로, main 병합·운영 배포를 수행하지 않는다. [Worklog](worklogs/2026-10-05_skill-id-examples-review-pr.md).

## 2026-10-06 보존된 공고 분석 운영 요청 로그 문서화

- 기존 공고 분석 증거 파일을 2026-10-01 배포 revision `malhaebom-mk2-ncs-recheck-2248`의 추천 200·원문 분석 201·세션 생성 201 기록 중심으로 수정했다. [운영 API 증거](evidence/job-source-analysis-e2e-2026-10-01.md).
- 원래 로컬 인증 E2E는 [로컬 원본](evidence/job-source-analysis-local-e2e-2026-10-01.md)에 그대로 보존했다. 운영 로그의 인용·저장 상세와 동일 사용자 연결은 미확인이다. 새 E2E는 실행하지 않았다.

## 2026-10-04 도메인 확장 제외 문구 정리

- 사용자 요청으로 공고 탐색·추천·원문 자동 분석·기업 조사·공급자 및 직무·질문 유형 확장을 일괄 제외하는 문구를 제품 문서, 제안서와 원본, 체크포인트, 초기 Spec·관련 작업 기록에서 삭제했다.
- 기능 구현이나 검증 완료를 추가로 주장하지 않는다. 원문 검증·개인정보 보호·평가 사실·RAG/LangGraph 금지·채용 적합성 및 합격 가능성 판단 금지는 유지한다. [Worklog](worklogs/2026-10-04_domain-expansion-scope-cleanup.md).

## 2026-10-02 D10 관측 가설·D11 공식 baseline 오프라인 준비

- 운영 사용자 수동 E2E와 Langfuse 코칭 성공 trace는 이미 확보했으나, `skill_version=interview-coach-v6` 표시값과 현재 로컬 카탈로그 v6.1의 불일치 및 `default` Environment와 운영 리비전의 연계는 미확인이다. [D10 관측 기반 가설·사후 검증 계획](experiments/2026-10-02_d10-observability-hypotheses.md)에 한 줄 개선 가설을 작성해 D10 해당 **문서 항목만 완료** 처리했다. #162의 코드 병합과 실제 운영 배포·검증은 별개다.
- [D11 사전점검](experiments/2026-10-02_d11-baseline-preflight.md)과 `evals/prepare_d11_baseline.py`로 Dataset v2 30건 및 기존 인젝션 3건, 로컬 Prompt/Skill 결합 해시를 오프라인으로 고정하는 준비 절차를 마련했다. 실제 운영 릴리스·유료 baseline·신규 인젝션 3건·최신 v5 사람 평가는 **미확인/미실행**으로 유지한다. [Worklog](worklogs/2026-10-02_d10-d11-eval-preflight.md).

## 2026-10-02 평가 증거·누락 항목 교차검증 (문서 정리)

- 기존 `EVAL_REPORT.md` 4·6·7장 수치와 원본 실험을 [증거·누락 점검표](experiments/2026-10-02_evaluation-evidence-gap-audit.md)로 연결했다. 동일 Skill v4/v5 **2,048-token·45초 페어 비교**, v5 **2,048-token·60초 단독 실행**, v5 **4,096-token·60초 후속 실행**은 서로 다른 측정이다. 과거 v4 팀 품질 취합과 D4 Dataset 정답표 검토도 현재 v5 사람 평가와 별도로 유지한다.
- 4,096-token v5 자동 불일치 7건 검토 양식은 [PR #161](https://github.com/aihuman-7th/proj2-3/pull/161)로 병합됐지만, 새 v5 사람 점수·critical 판정은 미입력이다. [PR #162](https://github.com/aihuman-7th/proj2-3/pull/162)는 이미 병합된 별도의 **Prompt·Skill 실행 버전 기록 수정**이며 사람 검토 완료와 무관하다. final 비용 상한, D11 운영 baseline과 단일 변경·주입 3건 전후, D10 production trace 및 같은 요청 PlayMCP 직접 분석 증거도 여전히 미확인이다. 이번 작업은 원본 재채점·신규 provider 호출·운영 배포를 수행하지 않았다. [Worklog](worklogs/2026-10-02_eval-evidence-gap-audit.md).

## 2026-10-02 코칭 Prompt·Skill 실행 버전 기록 정합성

- 로컬 기본 Skill 버전 메타데이터를 실제 `skills/interview-coach/criteria.json` 카탈로그에서 읽도록 변경했다. 코칭 서비스는 조립에 사용한 Prompt·Skill 버전을 Supabase `coaching_runs`에 명시적으로 전달하고, API 관측값에서도 실행 서비스 버전을 우선한다. 원격 Langfuse 관리형 Prompt를 실제로 선택하면 해당 원격 버전(예: `malhaebom-coaching@7`)을 보존한다.
- Langfuse SDK 4.15.1 환경에서 분리·Prompt·런타임·진단·DB 저장·관측·자산 테스트 70건 통과. 기존 개발 환경의 Langfuse 2.60.10에서는 SDK API 차이로 일부 테스트가 실패했다. 운영 이미지·원격 관리형 Prompt 본문 및 production trace는 검증하지 않았으며, 판정 규칙·평가 점수·실제 배포 설정은 변경하지 않았다. [Worklog](worklogs/2026-10-02_coaching-version-provenance.md).

## 2026-10-02 Gemini v5 4,096-token 출력 계약 재검증

- 동일 v5 Prompt·Skill·합성 30건을 최대 출력 4,096 tokens와 timeout 60초로 실제 Gemini에 재실행했다. 계약 30/30, provider 종료 사유 `stop` 30/30, 실패 0건, 규칙 기반 정확도 92.6%, p50/p95 4.393초/6.167초, 알려진 비용 $0.171308을 기록했다.
- 이전 2,048-token 실행의 `coach-failure-26` JSON 절단은 재현되지 않았다. 출력 한도·timeout이 다르므로 v4/v5 품질 비교를 대체하지 않으며, 7개 자동 의미 판정/근거 불일치와 사람 검토·운영 E2E 미검증은 남는다. [실험](experiments/2026-10-02_gemini-v5-4096-30case-evaluation.md), [Worklog](worklogs/2026-10-02_1045_gemini-v5-4096-contract-recheck.md).
- 자동 불일치 7건만 계약 유효 attempt ID별 local 사람 검토 양식으로 추출하는 도구를 추가했다. 검토 점수·critical failure는 아직 미입력(null)이며, 이 준비만으로 semantic 품질 통과나 강사 판단 해결을 주장하지 않는다.

## 2026-10-02 최신 영문 v5 Prompt 평가 보고서 정합성

- 같은 현재 Skill에서 v4/v5를 각각 합성 30건 실호출했다. 두 후보 최초/최종 계약 30/30, 종합 자동 통과 v4 22/30 → v5 20/30, 비용 $0.19638110 → $0.17027067, 응답 완료 p95 4.621초 → 4.622초다. 보정 0회이며 TTFT는 미측정이다.
- `EVAL_REPORT.md` 4·6·7장에 버전·전후 표·회귀 문항·출시 게이트를 채웠다. 최신 v5의 경계·실패 유도 자동 게이트는 미달하며 새 사람 평가·운영 E2E·비용 상한은 미검증/미정이다. 운영 Prompt·모델·배포·Langfuse·Git 원격 상태는 변경하지 않았다.
- [실험](experiments/2026-10-02_latest-english-v5-comparison.md), [Worklog](worklogs/2026-10-02_latest-english-v5-eval-report.md).


## 2026-10-01 코칭 도메인 규칙을 Skill에서 관리 (로컬 수정)

- 기본 Prompt를 `coaching-v5-skill-owned`, Skill을 `interview-coach-v6.1-domain-rules`로 갱신했다. 판정 의미·우선순위·긍정/부정 예시는 Skill이 관리하며 새 영문 Prompt는 입력·출력 계약만 정의한다.
- 결과 검증의 상충하는 예시는 기존 Skill의 방법·조건과 관찰 결과 기준으로 통일했다. 실제 수치나 반복 횟수를 일괄 필수 조건으로 요구하지 않는다.
- v4 및 이전 템플릿과 기존 평가 자료는 보존했다. 과거 실행 재현에는 당시 Skill도 필요하다. 실제 `.env`와 Langfuse 관리 템플릿이 이전 버전을 지정하면 새 기본값을 적용하려면 별도 갱신이 필요하다.
- 이번 변경은 컨테이너 재빌드·운영 배포·Langfuse 원격 갱신·LLM 재평가를 포함하지 않는다. Cloud Run은 사용자 요청에 따른 중지 상태를 유지한다.
- 관련 테스트 127건 통과. 로컬 `.env`의 버전 두 항목을 새 버전으로 맞췄으며 현재 실행 이미지는 다음 재빌드/재시작 전까지 이전 버전을 사용한다. [Spec](specs/coaching-domain-rules-in-skill.md), [Worklog](worklogs/2026-10-01_coaching-domain-rules-in-skill.md).


## 2026-10-01 로그인 사용자 공고 원문 분석 E2E

- local Supabase 실제 로그인 사용자 JWT로 연습 준비 API 흐름을 재현했다. 최종 run은 `skill-server` 기준 공고 3건을 반환했고, 선택한 사람인 공고 원문을 다시 검증해 요구사항 5건을 추출했다.
- 모든 요구사항의 원문 `source_excerpt` 존재와 서버 quote 검증 gate 통과를 확인했고, 검토 공고가 해당 로그인 사용자의 `private_job` 목록에 저장·조회된 뒤 요구사항 2개를 선택해 `preset-04` 연습 세션 생성까지 성공했다.
- 실행 시점의 PlayMCP 인증은 503이어서 저장소의 기존 `web` provider 복귀 경로를 사용했다. 증거에는 JWT, 사용자 ID, 공고 전체 URL/원문, 요구사항 원문/인용, 저장 UUID를 남기지 않았다.
- 이 결과는 실제 브라우저 로그인 세션의 JWT를 사용한 인증 API E2E이며 브라우저 클릭 영상 검증과 운영 배포 검증은 별도다. [로컬 Evidence](evidence/job-source-analysis-local-e2e-2026-10-01.md), [Worklog](worklogs/2026-10-01_1400_job-source-authenticated-e2e.md).

## 2026-10-01 사용자 제공 코칭 시스템 프롬프트

- `coaching-user-supplied-v4-verification`을 기본 코칭 Prompt로 선택한다. 첨부한 영문 원문을 별도 템플릿으로 추가하고 현재 Skill을 결합한다. `.env.example`도 같은 버전으로 맞췄으며 기존 v4.2와 과거 빌더는 보존했다.
- Skill·출력 스키마·MCP·서버 검증과 단일 호출 구조는 유지한다. 배포·Langfuse 게시·실제 사용자 E2E와 모델 품질 개선은 검증하지 않았다. 기존 로컬 두 단계 후보 실험은 범주별 품질 승격 기준을 충족하지 못했으며, 사용자 요청으로 프롬프트 기본값만 교체한다.
- [Spec](specs/user-supplied-coaching-prompt-default.md), [Worklog](worklogs/2026-10-01_user-coaching-system-prompt-pr.md).

## 2026-10-01 MCP gateway 실패 사용자 경로 검증

- 로그인 사용자 로컬 Compose에서 공고 선택·WAV 분석·answer revision 저장 뒤, 테스트용 `MCP_SERVER_SCRIPT`를 존재하지 않는 경로로 주입해 stdio MCP subprocess 시작 실패를 재현했다.
- `/api/agent`는 두 차례 HTTP 503과 `state=mcp_error`, `code=COACHING_MCP_UNAVAILABLE`, `retryable=true`을 반환했고, 화면은 재시도 안내를 표시했다. API 로그에는 MCP 실행 실패와 `failure_stage=context`가 기록됐다.
- 이 검증은 로컬 Compose 사용자 흐름이며 외부 배포·Langfuse Cloud trace 검증은 남아 있다. [Worklog](worklogs/2026-10-01_0945_d9-mcp-failure-contract.md).

## 2026-09-30 기록 결과의 비교·대화 접기

- 연습 기록 결과·상세에서 1·2차 답변 비교와 완료된 꼬리질문 대화를 기본 접힘으로 표시한다. 대화 보관 API는 PR #130에서 제공한다. [Spec](specs/history-comparison-chat-folds.md), [Worklog](worklogs/2026-09-28_1733_history-comparison-chat-folds.md).

## 2026-09-30 완료 면접 대화 기록 API

- 종료된 면접 대화는 기존 2차 `analysis_jobs.result.interview_chat`에 저장한다. 조회 시 두 답변의 revision·코칭 시각·model/Prompt/Skill/criteria 버전 12개 fingerprint와 만료를 확인한 뒤 노출한다. [Spec](specs/history-comparison-chat-folds.md).

## 2026-09-30 사람인 MCP + Tavily 잡코리아 검색 코드

- 선택형 `playmcp_tavily` 모드가 사람인 MCP와 Tavily 잡코리아 검색을 합친다. 기존 두 사이트의 개별 URL 허용 목록·공고 원문 검증·근거 매칭을 통과한 후보만 표시한다. `TAVILY_API_KEY`가 없으면 새 모드는 설정 오류를 낸다.
- 로컬 실행 컨테이너에서 잡코리아 1건·사람인 2건을 확인했다. 로그인 사용자 화면에서 공고 선택·저장까지의 검증은 남아 있다. [Spec](specs/playmcp-tavily-jobkorea-search.md), [Worklog](worklogs/2026-09-30_0925_playmcp-tavily-jobkorea.md).

## 2026-09-30 Skill별 폴더 구조

- 코칭 Skill 파일과 기준 카탈로그를 `skills/interview-coach/`, 면접 대화 Skill을 `skills/interview-conversation/`으로 이동했다. 로더·평가 기본 경로·현재 문서 링크를 갱신했고 Skill 내용은 변경하지 않았다. [Worklog](worklogs/2026-09-30_1152_skill-folders.md)를 따른다.

## 2026-09-29 코칭 실패 진단

- `/api/agent`의 요청별 실패 단계·고정 오류 코드·계약 시도 이력을 기존 trace ID와 함께 기록한다. 원문·토큰·예외 메시지는 새 로그에 넣지 않는다. [Spec](specs/coaching-failure-diagnostics.md), [Worklog](worklogs/2026-09-29_0943_coaching-failure-diagnostics.md).

## 2026-09-29 Prompt와 도메인 Skill 분리

- 코칭·README 분석·공고 요구사항 분석·면접 대화의 역할·응답 형식은 `prompts/`, 판정·원문 근거 규칙은 `skills/`에 둔다. 요청 구성 시 둘을 결합하며 README·공고 분석에도 실제 Skill 본문을 적용한다.
- 신규 코칭 기본 Prompt는 `coaching-output-v4.2`다. 기존 v3/v4/v4.1 빌더는 동일 Skill 입력에서 문자열을 보존한다. 과거 전체 입력 재현에는 당시 Skill 파일도 필요하다.
- Langfuse 동기화 계획은 Skill 슬롯이 있는 템플릿을 만들고 런타임은 현재 Skill을 결합한다. 슬롯 없는 과거 원격 완성 Prompt는 로컬 템플릿으로 fallback한다. Cloud 게시·실행 컨테이너 갱신·실제 모델 품질 비교는 수행하지 않았다.
- API·MCP·출력 스키마·루브릭·서버 검증은 유지한다. 로컬 통합 체크아웃에서 백엔드 전체 547개, 분리 PR 브랜치에서 525개 테스트가 통과했다. [Spec](specs/prompt-skill-separation.md), [원 작업 기록](worklogs/2026-09-29_2109_prompt-skill-separation.md), [PR 추출 기록](worklogs/2026-09-30_prompt-skill-separation-pr.md)을 따른다.

## 2026-09-28 이미지 전용 공고 선택 오류 수정

- 사용자가 선택한 메일플러그 공고(`rec_idx=55032635`)는 실제 모집 상세가 이미지뿐이었다. 기존 추출기는 주변 개인정보 안내·복리후생 542자를 분석에 전달했고 원문 기반 요구사항 검증에서 503이 발생했다.
- 사람인의 `user_content` 상세 텍스트만 추출하도록 수정했다. 해당 영역이 이미지뿐이거나 20자 미만이면 추천에서 제외하며, 이미 표시된 카드의 선택도 LLM·목록 조회·저장 전에 거부하고 원인을 안내한다. 이미지 OCR은 지원하지 않는다. 기존 웹검색 구현, 원문 인용 검증, API·화면 계약은 유지한다.
- 관련 추천 테스트 39개와 PlayMCP 테스트 14개, 격리된 backend 전체 338개가 통과했다. API만 재빌드해 `8c51d6bc6185` healthy를 확인했다. 기존 frontend `a097d23271ce`를 유지했다.
- 실행 이미지의 TestClient에서 실제 원문·실제 모델(`google/gemini-3.5-flash-lite`)로 펄포즌 Java/Spring 공고를 분석했다. HTTP 201, 요구사항 5개, 모든 인용의 상세 본문 일치, 약 5.491초를 확인했다. 실제 PlayMCP 추천 API도 HTTP 200으로 이미지 공고를 제외한 3건을 약 2.090초에 반환했다. 단일 측정이며 지연 보장은 아니다.
- 위 실호출은 테스트 인증과 메모리 저장소를 사용했다. 실제 사용자 DB 저장·로그인 브라우저부터 코칭까지의 E2E는 검증하지 않았다. 기존 화면에 남은 메일플러그 카드는 `다시 검색`으로 갱신한다.
- [Spec](specs/saramin-backend-recommendations.md), [Worklog](worklogs/2026-09-28_1635_saramin-image-only-source.md).
## 2026-09-28 PlayMCP 게이트웨이 모듈

- PlayMCP 사람인 직접 호출과 서버 전용 token 갱신 모듈을 추가했다. 이 단계는 모듈·인증/URL 검증 테스트이며 추천 공급자 factory와 Compose 연결은 후속 PR에서 적용한다.
- 사용자 README/NCS는 전송하지 않고 고정 검색어와 허용된 사람인 공고 URL만 사용한다. 인증 파일은 Git·이미지에서 제외한다. 기존 인증 파일도 열린 파일의 mode가 0600일 때만 읽으며, 0644 등은 읽기·갱신 전에 거부한다.
- [Spec](specs/playmcp-job-search.md), [Worklog](worklogs/2026-09-28_1648_playmcp-module-pr.md).
## 2026-09-28 코칭 완료 후 결과 상단 이동

- 1차 코칭·답변 비교가 완성되면 가장 최근 결과의 시작점을 채팅 상단 24px 아래로 이동한다. 로딩 말풍선의 class 변경도 감지하며 바로 추가되는 일반 메시지가 읽는 위치를 덮어쓰지 않는다.
- 사용자가 하단으로 돌아오면 일반 메시지의 하단 따라가기를 재개한다. README 결과 이동은 유지한다.
- 구현 당시 훅 10개·frontend 전체 97개 테스트와 build, 테스트 데이터의 실제 컴포넌트 브라우저 검증을 통과했다. 로그인 녹음·모델·저장 E2E는 재실행하지 않았다.
- [Spec](specs/coaching-result-scroll.md), [Worklog](worklogs/2026-09-28_1550_coaching-result-scroll.md).
## 2026-09-29 Langfuse provider 지연시간과 실제 호출 검증

- `coaching.provider` generation을 provider HTTP 요청 **직전**에 시작하고, 응답·오류 처리 뒤 같은 generation을 update/end 하도록 변경했다. 따라서 Langfuse의 Duration은 관측 SDK 호출 시간이 아니라 provider HTTP 호출을 둘러싼 실제 처리 구간을 표시한다.
- Japan Cloud test project에서 비식별 고정 service-integration fixture 3건을 실제 `google/gemini-3.5-flash-lite`로 호출했다. 모든 요청은 HTTP 200·출력 계약 검증 통과·무재시도였고, provider generation의 Langfuse start/end 차이는 `coach-normal-01` 3.892초, `coach-boundary-13` 3.206초, `coach-failure-30` 2.666초였다. 각 비용은 $0.005737, $0.005706, $0.005459였으며 토큰과 model도 generation에 기록됐다.
- 이 검증은 실제 LLM provider와 Langfuse Cloud를 대상으로 했지만, 사용자 DB/MCP가 아닌 고정 fixture를 사용했다. 실제 로그인 사용자 trace와 retry는 같은 날 후속 E2E에서 별도로 확인했으며, Prompt production 승격/rollback 검증은 별도 과제로 남긴다. 재현 절차와 trace ID는 [Worklog](worklogs/2026-09-29_1054_langfuse-provider-duration.md)를 따른다.

## 2026-09-28 면접 대화 리뷰 수정

면접 대화는 두 코칭 run의 model·Prompt·Skill·실제 criteria 버전을 확인하고 현재 질문의 기준 버전과 일치할 때만 시작한다. 새 코칭 run은 서버 question의 `criteria_version`을 저장하며 과거 null 값은 추정하지 않는다. 성공한 요청 ID·입력·응답은 대화 수명 동안 재사용하고 같은 ID의 다른 입력/action을 차단한다. 관련 검증과 새 migration 적용 범위는 [Worklog](worklogs/2026-09-28_1605_interview-chat-review-fixes.md)를 따른다.

## 2026-09-28 면접 대화 종료 후 이동

종료 성공 후 다시 면접하기(/practice)와 홈으로 가기(/) 링크를 표시한다. 새 문서 탐색으로 현재 연습 UI를 초기화하며 인증·저장 기록은 유지한다.

## 2026-09-28 공통 LLM SDK 전환

공통 JSON provider는 OpenAI SDK로 호출하며 SDK retry=0과 main의 전송 재시도·비용 제한·서버 계약 검증을 유지한다. 웹검색 전용 호출은 별도다.

## 비교 후 면접 대화 화면

내용 비교가 준비되면 첫 질문을 요청하고 같은 채팅에서 사용자 질문/답변과 종료 요약을 표시한다. 실패 재시도·새 대화 복구·중복 전송 차단을 제공하고 비교 이후 공고 검색 입력을 숨긴다. 사용자가 이전 내용을 읽을 때는 강제 스크롤하지 않는다.

start의 409는 과거 기록·코칭 준비 조건에 따른 대화 불가 상태로 안내하며 비교 결과를 유지한다. 이 상태에는 재시도·새 대화 버튼·입력 폼을 표시하지 않는다. 시작 연결 실패는 기존 재시도, 진행 중 대화의 404/409는 기존 새 대화 복구를 유지한다 ([Worklog](worklogs/2026-09-28_1605_interview-chat-ui-review-fix.md)).

## 2026-09-28 비교 후 면접 대화 API

인증된 `/api/agent/chat`은 두 코칭과 비교가 준비된 사용자 소유 세션에서 첫 질문·메시지·종료 요약을 반환한다. 원래 기록을 쓰지 않으며 임시 대화는 단일 API 프로세스에서만 유지된다. SDK·화면 연결은 후속 PR이다. API 테스트 결과는 해당 Worklog에서 확인한다.

## 2026-09-28 기본 질문 1~10번 코칭 연결

기본 질문 10개를 질문별 서버 문맥과 활성 기준으로 연결한다. 기존 문제 해결 6개 기준과 draft.3, main의 비용·재시도·관측·HTTP MCP 구조를 유지한다. 새 질문에도 인증·소유자·만료·인용 검증을 적용한다. API·MCP 계약 회귀 검증은 별도 PR Worklog에 기록하며 기존 로컬 실행 증거와 구분한다.

> 이 문서는 날짜별 검증 기록을 누적한다. **상단의 최신 날짜 섹션과 아래 구현·호출 경로 표가 현재 상태를 우선해 설명하며**, 더 아래의 과거 날짜 섹션은 당시 snapshot으로만 읽는다. 세부 코칭 계약은 [저장소 구현 점검표](repository-audit.md)와 [코칭 런타임 계약](specs/coaching-skill-runtime.md)을 함께 확인한다.

> 2026-09-17 정적 코드 audit. 기준: `origin/main` `73525a159e3faa61114d968e6dbdd14d0fb85a82`, 코드 이관 PR #1. **이관 반영, 런타임 검증 전**. 설치·모델 다운로드·서비스 실행·배포·학습·benchmark는 수행하지 않았다.

## 판정 기준

- `STATIC_CONFIRMED`: 파일과 호출 경로를 읽어 확인. 실제 동작 성공을 의미하지 않는다.
- `PARTIAL`: 일부 구현은 있으나 목표와 차이 또는 확인된 제약이 있다.
- `SCAFFOLD`: 양식·예시·TODO만 존재한다.
- `UNKNOWN`: 실제 환경·자산·품질 미확인.
- 기존 `VERIFIED_ACTIVE`, `VERIFIED_UNUSED`, `BROKEN`은 실행 또는 충분한 별도 증거가 있을 때만 사용한다. 이번 audit는 실행 성공 판정을 내리지 않는다.

## 2026-09-28 STT 동적 initial prompt

- persistent 분석 경로는 사용자가 선택한 practice session의 직접 입력 질문, 검수 공고 제목, 선택 요구사항에서 allowlist 기술용어를 최대 12개 추출해 faster-whisper `initial_prompt`로 전달한다.
- hint 문맥은 클라이언트가 직접 보내지 않고 기존 사용자 JWT/RLS 범위에서 서버가 다시 조회한다. 문맥 조회 실패나 매칭 용어 없음은 기존 no-prompt STT로 fallback한다.
- extractor, transcriber 전달, Supabase 문맥 조회, persistent analysis API 회귀 테스트를 통과했다. 실제 신규 미공개 acceptance 녹음에서의 품질 검증은 아직 수행하지 않았다.
- frozen 30건 dev/diagnostic parity에서 서비스 기본 CPU/int8은 core normalized CER 1.94%, WER 4.59%, p50 3.02초였고 CUDA/float16은 CER 2.44%, WER 5.27%, p50 0.27초였다. CUDA는 약 10.9배 낮은 RTF를 보였지만 real-30에서 tail hallucination 1건이 관찰됐다.
- 따라서 제품 기본 runtime은 이 실험만으로 변경하지 않는다. 현재 CPU 수치는 로컬 Ryzen 데스크톱 기준이며, 새 multi-speaker acceptance set과 실제 배포 E2E 검증이 남아 있다.
- 실제 배포 E2E 검증을 위해 /analysis-jobs의 POST→202, 202→terminal, total latency와 server STT/RTF를 수집하는 benchmark CLI 및 process 단계별 analysis_timing 로그를 추가했다. 로컬 Docker와 benchmark 전용 Cloud Run에서 2/4/8 vCPU CPU scaling을 측정했으며 Hosted Supabase/RLS persistence 검증은 후속 단계다.
- Cloud Run CPU benchmark image는 CPU-only PyTorch와 pre-baked large-v3-turbo를 사용하는 별도 Dockerfile로 검증했다. 로컬 image size는 3.444GB→1.934GB, Cloud Build는 589.1s→266.6s로 줄었고 4 vCPU rollout 후 첫 요청은 35.792s→17.249s로 감소했다. steady-state STT latency는 기존 4 vCPU와 같은 수준이었다. 이후 build-time 모델 다운로드를 기존 실험의 immutable revision `0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`로 고정하고 image label에 남겼다. 앞의 실측값은 고정 전 이미지 결과이며 고정 후 이미지의 build·성능 재검증은 아직 수행하지 않았다.

## 2026-09-22 Prompt harness v4.1 final

- 운영 local fallback과 모델 비교 runner의 system prompt 조립을 `backend/app/services/coaching_prompt.py`의 canonical builder로 통합하고 기본 prompt를 `coaching-output-v4.1`로 올렸다. 과거 v3/v4는 평가 재현용으로 유지한다.
- v4.1은 evidence 키를 `segment_id`+`quote`로 고정하고 criterion evidence 존재, next action target ID 범위를 명시한다. 계약 실패 시 이전 출력과 실제 검증 오류를 넣은 repair prompt로 1회 보정하며 새 사실·숫자·역할·기술·성과 생성을 금지한다.
- 평가 runner는 동일 builder/repair를 사용하고 prompt SHA-256, 반복 실행, 다중 `--case-id` 선택을 지원한다.
- 최종 Flash-Lite / Dataset v2 30건 × 3회에서 1차 계약 84/90(93.3%), repair 6/6 성공, 최종 계약 90/90(100%)을 확인했다. 2026-09-30 D4 사람 검토에서 `coach-boundary-17` V expected를 `partial → undetermined`로 수정한 뒤 동일 90개 저장 출력을 provider 재호출 없이 재채점한 결과, 최종 execution 기준 label은 316/360(87.8%) → 313/360(86.9%), V는 77/90(85.6%) → 74/90(82.2%)로 정정됐다. evidence 96.0%, ID reference 100%, E2E p50 2,954ms / p95 5,395ms, 총 비용 $0.292000은 변하지 않았다.
- 30 case 중 21개는 3회 동일 label signature, 9개는 boundary 중심으로 변동했다. 별도 v4.2 few-shot과 criteria draft.2 실험은 전체 분포 회귀 때문에 채택하지 않았고 상세 결과는 worklog에 보존한다.
- 최종 구현 기준은 `coaching-output-v4.1 + problem-solving-v4-draft.3 + contract repair`다. 원인 근거는 관찰 신호(`cause_observation`)와 원인 후보를 좁힌 연결(`cause_inference`)로 분리해 판정한다. 두 기준은 구버전 결과와 직접 비교하지 않으며, Langfuse managed prompt production 승격/rollback은 별도 후속 작업이다.

## 2026-09-21 코칭 런타임 보강

- `POST /api/agent`의 실제 OpenAI-compatible provider는 timeout·연결 오류·`429`·`5xx`를 설정된 최대 전송 횟수 안에서 재시도하고, `Retry-After`와 지수 backoff를 최대 대기값으로 제한한다. 비재시도 `4xx`는 즉시 실패한다.
- JSON parse와 Pydantic·서버 참조 출력 계약은 보정 prompt로 최대 2회 시도하며, provider가 보고한 요청 누적 비용이 설정 상한을 넘으면 추가 호출과 응답 사용을 차단한다.
- FastAPI에 인증된 stateless Streamable HTTP MCP를 정확히 `/mcp`로 연결했다. Supabase/E2E access token과 5분 이하 capability token의 사용자·scope·허용 ID를 함께 검증한다. `compare_attempts`는 별도 scope와 정확한 1차·2차 코칭 결과 ID를 요구하며 저장 결과만 비교한다. 내부 코칭 orchestration은 현재 stdio gateway를 유지한다.
- Langfuse Python SDK v4의 OpenTelemetry로 요청 trace, provider HTTP 시도별 generation, 출력 계약 검증별 span을 같은 trace ID로 기록한다. model·token·cost·latency·재시도·버전만 전송하며 답변·전사·공고·URL·evidence quote·token 원문은 보내지 않는다.
- Japan Cloud test project에 candidate Prompt version 1과 합성 Dataset 30건을 등록했고, redacted smoke trace 세 observation과 Prompt 연결을 Observations API v2에서 확인했다. 실제 provider trace와 Prompt baseline/candidate 평가·production 승격·rollback은 아직 확인하지 않았다.
- 2026-09-29에는 안전한 합성 fixture로 FastAPI `/api/agent` → 실제 OpenRouter `google/gemini-3.5-flash-lite` → 출력 계약 검증 경로를 3회 호출했다. 세 trace 모두 `coaching.analyze`, `coaching.provider`, `coaching.output_validation`을 같은 trace ID로 수집했고 generation에는 `malhaebom-coaching` v3 Prompt, token·cost·재시도 메타데이터가 연결됐다. 결과와 trace ID는 `docs/worklogs/2026-09-29_1040_langfuse-live-provider-verification.md`에 남겼다. 이 확인은 사용자 데이터·실제 MCP 문맥·운영 배포를 사용하지 않았으므로 운영 trace 증거는 아니다.
- OpenRouter 실제 서비스 통합 smoke에서 Flash-Lite와 Luna 모두 지원하지 않는 `temperature=0`을 전송해 `require_parameters` 라우팅이 404로 실패함을 확인했다. 서비스 요청은 temperature를 생략해 model default를 사용하고, OpenAI GPT-5 계열 strict schema는 모든 object property를 재귀적으로 required 처리하며, conservative한 markdown JSON code fence(` ```json `) unwrap을 적용했다.
- 2026-09-21 최종 2개 모델 x 3건 서비스 통합 검증에서, 1차 독립 하네스 smoke(Run 1)는 두 모델 모두 3/3 통과했으나, 2차 Docker + 로컬 Supabase E2E 실측(Run 2)에서는 `google/gemini-3.5-flash-lite`가 3/3 무재시도 통과(HTTP 200, Validator 통과, p50 3,440ms, p95 3,584ms [표본 3건 기준], 비용 $0.011)로 단일 기본 모델로 선정되었고, `openai/gpt-5.6-luna`는 parser 보정 후 2/3 통과(경계 케이스 복구 성공, 날조 유도 케이스는 모델 계약 실패 502)로 확인되었다.
- 로컬 Supabase(54321) + Docker 전체 스택(Frontend: 18080, Backend: 8000)에서 사용자 가입/로그인부터 공고 선택, 연습 세션 생성, 음성 분석, 답변 확정, `/api/agent` 코칭 응답, `coaching_runs` Supabase DB 저장까지 전체 E2E 파이프라인 통과를 확인했다.
- 2026-09-29에는 실제 로그인 사용자 흐름에서 WAV 업로드/STT → `/api/agent` → stdio MCP-backed coaching service → OpenRouter → output validation → persistence까지 실행하고 Langfuse 성공 trace `7f67f14ceb9040868bad4249903c79a8`을 확인했다. trace에는 `google/gemini-3.5-flash-lite`, 총 14,560 tokens, 약 $0.007367 비용과 최종 `needs_more_info` 상태가 기록됐다.
- 같은 검증에서 controlled network failure trace `edeb73e5d1424c9fa877c00509ef9473`의 1차 provider attempt가 `network_error / will_retry=true`, 2차가 `network_error / will_retry=false`로 기록되는 것을 확인했다. 별도 trace `e3a9b8c176584a0faae688aaf537dda6`에서는 provider와 output validation이 성공했지만 로컬 Supabase의 `coaching_runs.criteria_version` migration 누락 때문에 persistence가 실패해 최종 503 `provider_error`로 기록됐다. pending migration 적용 뒤 같은 사용자 흐름이 정상 완료됐다. `CoachingRunPersistenceError`가 provider 계열 오류와 같은 API 상태로 정규화되는 점은 후속 진단성 개선 후보다.
- 2026-09-29 실제 로그인 사용자 UI에서 D6 Agent normal/boundary/injection 3종을 재검증했다. 세 요청 모두 코칭 응답까지 완료됐으며, normal은 질문 의도와 여러 근거 항목을 인정하면서 개인 행동·선택 이유·공고 연결의 부족을 추가 요청하는 `needs_more_info`, boundary는 부족 근거 중심의 `needs_more_info`, injection은 평가 조작 지시를 따르지 않고 `off_topic`/근거 미관찰과 `needs_more_info`로 처리됐다. 프로젝트 정책상 normal 입력도 근거가 부족하면 `needs_more_info`가 정상 결과이므로 D6 synthetic evidence의 normal 허용 상태를 `ok | needs_more_info`로 맞췄다.
- 같은 날 normal case를 1차 답변으로 유지한 뒤 코칭에서 부족하다고 표시된 개인 행동·행동 선택 이유·공고 연결을 보완해 2차 답변을 제출하고 비교 화면까지 완료했다. 기준별 내용 비교에서 1차 일부 확인/미확인 항목이 2차 확인으로 바뀌었고, 동일 WAV를 재사용한 전달력 수치는 1·2차 동일하게 표시돼 실제 저장 데이터 기반 1차→코칭→2차→비교 E2E를 확인했다.

- Docker의 현재 backend 전체 단위 테스트 274개가 통과했다.

## 2026-09-22 평가 러너 실패 격리

- OpenAI-compatible/Ollama 모델 비교 호출을 요청별 자식 프로세스에 격리하고 `--timeout-seconds`를 넘긴 호출은 강제 종료하여 `timeout`으로 기록한 뒤 다음 사례를 계속한다.
- 강제 종료로 usage를 받지 못한 호출의 비용은 unknown으로 유지하고, provider 응답 후 JSON·Pydantic·서버 validator 검증에 실패한 호출은 응답에서 확보한 token·cost를 보존한다.
- 이 동작은 평가 runner의 진행을 보장하며 Ollama 서버 내부 GPU 계산 취소를 보장하지 않는다. 실제 Qwen3/EEVE 30건 재실행은 아직 수행하지 않았다.

## 구현·호출 경로

| 영역 | 상태 | 실제 근거와 범위 |
| --- | --- | --- |
| Frontend | STATIC_CONFIRMED | [main.tsx](../frontend/src/main.tsx) → [App.tsx](../frontend/src/App.tsx). React 18/TypeScript/Vite. `/`는 테마 전환이 가능한 시작 메인으로 진입하며, `/design`은 디자인 화면, `/demo/`는 데모 분기, 나머지는 App 상태 기반 화면 전환이다. 시작 메인에서 연습·기록으로 이동하고 녹음·전사 상태에는 각각 별도 코치 일러스트를 표시한다. |
| 녹음·분석 | STATIC_CONFIRMED | [RecordingPage](../frontend/src/pages/RecordingPage.tsx)의 브라우저 음성/WAV 처리 → [AnalysisPage](../frontend/src/pages/AnalysisPage.tsx)의 Bearer 인증 업로드·polling → `/analysis-jobs` |
| API | STATIC_CONFIRMED | [backend/main.py](../backend/main.py) → [app/main.py](../backend/app/main.py). `/health`, 분석 작업 생성·조회·삭제, `/practice-records`, 질문·코치 음성 API |
| STT·VAD·전달력 | PARTIAL | [persistent_analysis_jobs.py](../backend/app/services/persistent_analysis_jobs.py): VAD → practice session 기반 동적 기술용어 `initial_prompt` → faster-whisper → DeliveryAnalyzer. hint 조회 실패는 no-prompt로 fallback한다. 코드·회귀 테스트는 확인했지만 새 acceptance 녹음 품질 검증은 미실행. [delivery_analysis.py](../backend/app/services/delivery_analysis.py): CPM·긴 침묵·반복 표현·피드백 선택 |
| 질문 TTS | PARTIAL | [app/main.py](../backend/app/main.py): 검수 자산 조회와 API 프로세스 내 Qwen 질문 합성/stream 초기화. CUDA·로컬 모델·저장 설정이 필요하며 실패 시 unavailable |
| 코치 TTS | PARTIAL | [coach_tts.py](../backend/app/services/coach_tts.py) → 별도 [tts_worker/app/main.py](../backend/tts_worker/app/main.py). [ResultPage](../frontend/src/pages/ResultPage.tsx)가 improvedAnswer의 PCM stream 재생을 요청하는 경로 존재 |
| 기존 내용 피드백 | PARTIAL | [question_rubric_generator.py](../backend/app/services/question_rubric_generator.py): Ollama `qwen3:8b` 기본값. `LLM_FEEDBACK_ENABLED=false` 기본 비활성. 활성 시 전사 직후 feedback와 전체 improved_answer 생성. `evaluate()`의 score는 상수 0이며 의미 품질 점수 아님 |
| 저장·기록 | PARTIAL | [supabase_persistence.py](../backend/app/services/supabase_persistence.py): 사용자 access token으로 DB/Storage 호출. 결과는 DB에 저장하지만 pending·progress는 프로세스 메모리. [local_analysis_jobs.py](../backend/app/services/local_analysis_jobs.py)는 메모리 대체 경로 |
| 인증 | STATIC_CONFIRMED | [supabaseAuth.ts](../frontend/src/api/supabaseAuth.ts): Google OAuth·세션. [auth.py](../backend/app/core/auth.py): JWKS, ES256/RS256, issuer/audience 및 sub 확인. DB 정책 적용·로그인 E2E는 UNKNOWN |
| 1차/2차·비교 | PARTIAL | 서버가 같은 질문·practice_session_id·attempt_no를 연결하고, 같은 공고·질문·model·Prompt·Skill 버전의 저장된 두 코칭 결과에 대해 criterion 상태·양쪽 근거·전달력 방향을 결정론적으로 비교한다. 비교 MCP 단위·HTTP transport 테스트는 통과했지만 운영 Supabase 데이터 E2E는 미확인 |
| 신규 에이전트 | PARTIAL | `/api/agent`, strict JSON provider·검증·저장, 네 MCP 읽기 도구(`compare_attempts` 포함), 인증된 HTTP `/mcp`, Langfuse v4 호출 단위 계측을 연결했다. 실제 provider를 포함한 로컬 Docker+Supabase E2E는 통과했지만 운영 배포·운영 JWT와 Langfuse Prompt production 승격/rollback은 미확인이다. |
| 평가 | PARTIAL | 최신 canonical prompt `coaching-output-v4.1`로 Flash-Lite / Dataset v2 30건 × 3회(90 executions)를 반복 측정해 최종 계약 90/90 통과를 확인했다. 2026-09-30 김재훈이 Dataset v2 30건의 사람 검토를 완료해 29건은 기존 판정을 확정하고 `coach-boundary-17`의 V는 `partial → undetermined`로 수정했다. 동일 저장 출력 offline 재채점 후 label 86.9%, V 82.2%이며 계약/evidence/ID/비용/지연은 기존 측정과 동일하다. 단일 검토자라 검토자 간 일치도는 없다. 100건 이상 공식 계약 준수율과 production Prompt 승격/rollback은 아직 완료되지 않았다. 상세 수치는 상단 2026-09-22 섹션과 [EVAL_REPORT](../EVAL_REPORT.md)를 따른다. |

## Historical snapshots

아래 날짜별 섹션은 당시 확인 상태를 보존한 기록이다. 이후 섹션이나 상단 현재 상태와 충돌하는 표현은 **과거 시점의 사실**이며 현재 상태 판정에 사용하지 않는다.

### 2026-09-18·2026-09-21 로컬 Google OAuth 실행 확인

- 기존 Google Cloud `malhebom` OAuth Web Client를 재사용하고 로컬 Supabase callback `http://127.0.0.1:54321/auth/v1/callback`을 승인된 redirect URI에 추가했다.
- 로컬 `supabase/config.toml`에서 Google Provider를 활성화했으며, 새 client secret은 Git에서 제외된 `.env`에서만 참조한다. 기존 호스팅 Supabase용 secret은 변경하지 않았다.
- 2026-09-21에 실행 중인 GoTrue가 이전 `127.0.0.1:3000` callback 설정을 유지한 것을 확인했다. 데이터 백업을 유지하는 재기동으로 `site_url=http://localhost:18080`, 허용 추가 주소 `http://127.0.0.1:18080`을 반영했다.
- 재기동 뒤 `/auth/v1/settings`의 Google Provider 활성화와 두 `18080` 주소에서 `/auth/v1/authorize`가 Google 계정 선택 화면으로 `302` redirect하는 것을 실행 확인했다.
- Google 동의 화면의 최종 `계속` 선택과 callback 이후 프런트 세션·FastAPI 인증 요청은 사용자 승인 대기 상태라 아직 E2E 완료로 판정하지 않는다.

### 2026-09-18 코칭 예시 답변

- `/api/agent`의 `ok`·`needs_more_info` 응답은 1~500자 `example_answer`를 반환하고, 종료 응답은 `null`을 반환한다.
- 서버는 확정 답변에 없는 숫자를 차단하며, Skill은 확인되지 않은 사실을 중립적인 자리표시자로 남긴다.
- 결과 화면은 예시와 사실 확인 안내를 표시하고, 기존 결과에서도 새 응답을 받을 수 있게 재요청 버튼을 유지한다.
- 최신 `main` 기준 백엔드 203개·프런트 38개 테스트와 production build를 통과했다. 실제 외부 LLM 응답 품질은 아직 검증하지 않았다.

### 2026-09-21 ALIO 진행 공고 검색

- 로그인 사용자는 공고 선택 화면에서 제목 키워드로 `GET /api/alio/recruitments`를 호출해 진행 중인 ALIO 공고를 최대 10건 확인할 수 있다.
- FastAPI만 `ALIO_API_KEY`를 ALIO 요청에 포함하고, 프런트 응답에는 기관명·제목·마감일·근무지·고용/경력 구분·안전한 원문 URL만 반환한다.
- 검색 결과는 검토 전 자료다. 기존 `GET /api/job-postings`의 `reviewed`·`is_active` 필터, 요구사항 1~2개 선택, `create_practice_session` 경로는 변경하지 않았다.
- 기본 URL은 공개 채용 조회 URL이다. 활용신청 후 제공되는 정식 URL 또는 인증키 파라미터명이 다를 수 있으므로 실제 명세가 확인되면 `ALIO_RECRUITMENT_API_URL`, `ALIO_API_KEY_PARAM`을 서버 환경변수로 맞춰야 한다. 키 유효성 자체는 공개 조회 URL이 키 없이도 응답하므로 검증하지 못했다.

### 2026-09-21 ALIO 원문 검토·1차 답변 조건

- 로그인 사용자는 ALIO 검색 결과에서 원문을 열고, 실제로 확인한 요구사항 1~5개와 각 원문 근거를 직접 입력해 `POST /api/alio/recruitments/review`로 저장할 수 있다. 제목만으로 요구사항을 생성하는 경로는 없다.
- 저장된 `data_origin='alio'` 공고·요구사항은 검토자 본인에게만 보인다. `reviewed_by_user_id`, RLS 정책, `create_practice_session` RPC가 다른 사용자의 열람·1차 답변 세션 생성을 차단한다. 팀 공용 검토자 역할은 구현하지 않았다.
- ALIO 검색 결과의 원문은 기관 채용 사이트일 수 있으므로 HTTP(S) URL을 허용한다. 이는 ALIO 검색에서 전달된 출처 링크를 저장하는 경계이며, URL 자체로 공고 내용의 진위를 서버가 재검증하지는 않는다.
- 선택한 요구사항 1~2개는 질문 선택 화면에 표시돼 1차 답변의 맥락을 제공한다. 이후 전사 확인·내용 코칭·재답변·비교는 기존 별도 경로이며 이번 변경에서 새로 구현·검증하지 않았다.
- 로컬 Supabase migration 적용, pgTAP 30개, 컨테이너 백엔드 테스트 13개, 프런트 단위 테스트 7개·production build, 로그인된 로컬 브라우저의 검색·검토 입력 화면 열기를 실행 확인했다. 실제 원문을 읽고 사용자가 제출하는 저장 E2E는 임의 공고 데이터를 만들지 않기 위해 수행하지 않았다.

## DB·인증·만료

[Supabase migrations](../supabase/migrations/)에 `analysis_jobs`, `question_tts_audio`와 비공개 `analysis-audio`, `question-tts-audio`, `preset-question-audio` bucket 정의가 있다. 사용자 테이블 정책은 `auth.uid() = user_id`, Storage는 사용자 경로를 검사한다. migration 파일 존재와 원격 적용 상태는 구분한다.

- 분석·질문 음성의 `expires_at` 기본값은 24시간이다. 만료 정리 script가 있으나 예약 실행은 확인하지 않았다.
- 기록 목록·완료 세션 조회는 만료 필터가 있지만, 단건 `get_job`·첫 시도 `get_attempt_one`과 RLS에는 만료 조건이 없다. 정리 전 만료 행 접근·재답변을 차단하지 않는 정적 문제 후보다.
- preset 음성은 공개 API가 허용된 asset ID를 서버 service role로 읽는다. 사용자 음성 조회와 다른 경계이며 실제 배포 키·권한은 확인하지 않았다.
- 백그라운드 작업은 FastAPI BackgroundTasks와 로컬 임시 파일에 의존한다. 서버 재시작 시 작업 재개를 보장하는 영속 queue는 없다.

## 실행 환경·배포 설정

| 항목 | 저장소에서 확인한 사실 |
| --- | --- |
| Python/Node | [Dockerfile](../Dockerfile) `python:3.12-slim`, [frontend/Dockerfile](../frontend/Dockerfile) `node:22-alpine` → `nginx:1.27-alpine`. 로컬 버전 강제 파일은 확인되지 않음 |
| Python 의존성 | [requirements.txt](../backend/requirements.txt): FastAPI 0.115.12, faster-whisper 1.2.1, silero-vad 5.1.2 등. STT/TTS/emotion별 requirements도 존재. 기본 requirements에 음성 runtime 포함, 모두 엄격 고정은 아님 |
| Frontend 의존성 | [package.json](../frontend/package.json): React ^18.3.1, Vite ^5.4.10, TypeScript ^5.6.3, Supabase JS ^2.112.3. npm/pnpm lockfile 공존, Docker는 npm ci 사용 |
| 환경 예시 | [루트 .env.example](../.env.example), [frontend/.env.example](../frontend/.env.example). 키 이름만 확인, 실제 secret 파일은 읽지 않음 |
| Compose | [docker-compose.yml](../docker-compose.yml): api 8000·frontend 18080 기본 포트, healthcheck. TTS Worker·DB·Langfuse 서비스는 포함하지 않음 |
| 배포 | [nginx.conf](../frontend/nginx.conf)의 API proxy, [vercel.json](../frontend/vercel.json)의 SPA rewrite. 2026-09-28 benchmark 전용 Cloud Run 서비스는 서울 리전에서 배포·health·STT 실행을 확인했다. 다만 Hosted Supabase/RLS를 포함한 production 배포는 아직 검증하지 않았다. |
| Script | [backend/scripts](../backend/scripts/): 전사, 만료 정리, 질문 음성 생성·업로드·TTS 평가. 실행하지 않음 |

## 문서와 구현의 차이 및 Issue 후보

2026-09-17 `gh issue list --state all --limit 100` 결과 0건. 아래는 정적 근거로 보고하는 후보이며 이번 작업에서 Issue 생성·코드 수정은 하지 않았다.

1. **비교 문구**: 긴 침묵·반복 표현의 증가/동일 입력도 ComparisonPage가 “줄었어요”로 출력한다. 예: 1→2에도 감소라고 표시. 조건별 문구가 필요하다.
2. **만료 접근**: 위 단건 조회·재답변 경로의 만료 차단 누락. `expires_at` 경과·cleanup 전 상황을 후속 테스트해야 한다.
3. **Compose TTS 주소**: `.env.example`을 복사하면 `TTS_WORKER_URL=http://127.0.0.1:8100`이 Compose의 host.docker.internal 기본값을 덮는다. API 컨테이너에서 호스트 Worker를 사용하려면 주소를 명시해야 한다.

기획의 전사 확인/revision/확인 질문/최대 2개 통합 행동/공고 연결은 기존 UI·LLM 경로와 다르다. 기존 전체 답변 생성은 현재 목표에서 제외되어 있으므로 재사용 시 경계를 수정해야 한다. 과거 TTS 문서의 “실시간 미구현”·STT 문서의 “VAD 미결합”은 현재 코드와 맞지 않는다.

## 인수·후속 검증

[음성 자산 인수 전 확인](experiments/2026-09-17_voice-asset-intake.md)에 모델·학습·데이터 참조·평가 기록의 위치와 미확인 사항을 모았다. [구현 계획](IMPLEMENTATION_PLAN.md)에 정적 조사와 실행 검증을 분리했다. 이번 코드 존재 확인을 GPU·브라우저·인증·RLS·만료·배포·모델 품질 검증으로 해석하지 않는다.

## 2026-09-18 평가 기반 후속 구현

`evals/run_model_comparison.py`에 OpenRouter 6종 basic/premium config, strict schema,
automatic provider routing, 모델 기본 temperature/reasoning 정책 및 호출별 raw/usage/cost 보존을 추가했다.
label/evidence/ID 지표·반복 label consistency·기본 실행 부모 참조·버전 해시를 기록한다.
실제 모델 품질·API 가격/지원·Premium recovery는 실행 검증하지 않았다. 세부 한계는 `evals/README.md` 참조.

### 평가셋 v2 (2026-09-18)

- 기존 dataset v1을 보존하고 동일 입력 30건의 expected label 재검토와 15건 semantic annotation을 v2에 반영했다. 독립 정답 검토 완료를 의미하지 않는다.
- intent/C/A/V를 독립 채점하며 requirement text 없는 v2의 job alignment/status와 job evidence를 고정 정확도에서 제외한다.
- 의미 품질은 근거 있는 사람 검토 0/1/2만 집계하고 미검토는 null이다. critical failure는 별도 발생률로 집계한다. runner는 case/run/attempt별 검토와 점수를 보존한다.
- R/D 추가 및 실제 LLM 호출은 수행하지 않았다.

### 평가 전용 Python 환경 (2026-09-18)

`evals/setup_env.sh`는 Python 3.12 프로젝트 로컬 `.venv-llm-eval`을 생성하고
운영과 공유하는 경량 requirements만 설치한다. ensurepip가 없으면 설치된 uv로 pip를 보완한다.
평가 CLI는 루트 .env를 override=False로 읽는다. OpenRouter는 OPENROUTER_API_KEY만 사용하여
MODEL_API_KEY 오선택을 방지하고 다른 endpoint에서는 기존 키 우선순위를 유지한다.
setup smoke는 실제 LLM API 호출 없이 import/help/mock 비교와 결과 저장을 검사한다.

### 실제 OpenRouter smoke (2026-09-18)

전용 venv에서 Qwen qwen3.8-flash/case 02 실제 요청을 수행했으나 계정 ZDR 정책으로
provider endpoint가 제외되어 HTTP 404였다. 실제 completion/usage/cost는 없어 null로 보존했다.
smoke 실패로 두 번째 사례 및 Basic 전체/Premium은 실행하지 않았다. 품질 결과로 해석하지 않는다.
기록: [실험](experiments/2026-09-18_openrouter-basic-smoke.md), local-results/openrouter-basic-20260918.

### Basic 실 API 부분 평가 (2026-09-18)

개인 키 smoke 성공 후 기존 설정으로 Basic 3종을 평가했다. 사용자 17:50(KST) 중단 지시에 따라
17:47:30 새 제출을 멈추고 17:49:51까지 진행 중 응답을 보존해 종료했다.
Basic 50건(Qwen17/DeepSeek17/Gemini16), 품질 실패32건, 빈 zero-token 응답1건은 품질 목록 제외.
Premium은 미실행. 보존된 실제 usage.cost 합계 $0.2431776446, 미확인 비용/진행 중 호출 없음.
critical 자동 검사 사례에 도달하지 않았고 사람 semantic/critical은 null이다.
부분 사례 수가 달라 최종 모델 비교/선정을 완료한 상태가 아니다.
기록: [실험](experiments/2026-09-18_openrouter-six-evaluation.md), local-results/openrouter-six-20260918T083814Z/REPORT.md.

### Basic 전체 및 Premium 복구 완료 (2026-09-18 재개)

사용자 재개 지시로 기존50건은 건너뛰고 Basic90건을 완료했다. 자동 품질 실패54건에만
Premium3종을 별도 부모 연결해162건 추가, 총252건 보존했다. Retry0/진행 중0/미확인 비용0.
Basic 품질통과는 Qwen8/30, DeepSeek13/30, Gemini14/30. Premium 자동복구는
DeepSeek Pro5/54, Sonnet5 11/54, GPT Terra8/54. 실제usage.cost campaign 합계 $4.0294520433612.
사람semantic/critical은 null, 제한된 자동critical은0/12검사이며 전체 안전성 통과를 의미하지 않는다.
주요Pydantic 조건오류는 not_observed의 evidence 및 비충족 needed 규칙이었다.
이전50/Basic90 원본 해시, 부모 연결, 실제 비용, 분위수를 검증했다. 모델/request 설정은 그대로다.
[실험](experiments/2026-09-18_openrouter-six-evaluation.md) 및 local-results/openrouter-six-20260918T083814Z/REPORT.md 참조.

### 자동 평가 정책 정렬 및 offline 재채점 (2026-09-18)

Skill과 grader의 intent독립/Vpartial 정책 차이를 정렬하고 not_observed의 부재·미확인
원문 인용을 schema에서 허용했다. 원문/ID/needed 검증은 유지한다. dataset v2의
승인된30건 label은 정책으로 재검증해 유지하고 지원segment/선택근거 정보를 추가했다.
v1은 보존한다. v2 evidence는 기준별 지원문장/실제부분인용 충실성을 채점하며 의미적
충분성은 사람검토 대상이다. prompt 기본버전은 coaching-output-v2, grader는 v4이다.
252건 raw원본을 보존한 재채점에서 Basic실패54→47, 공통실패12→9.
새Skill로 생성하지 않았으므로 변경된prompt의 실제준수/비용/latency를 검증한 결과가 아니다.
추가API호출 없음, 사람semantic/critical은 null.
결과: local-results/openrouter-six-20260918T083814Z/regrade-policy-aligned/REPORT.md.

### 새Skill Basic27회 실제API 정책 재검증 (2026-09-18)

지정공통실패9case에Basic3종만27회실행완료. Premium0/retry0/API오류0.
별도local-results/openrouter-policy-recheck-20260918에새응답/정책snapshot/비용/검증보존.
계약통과Qwen7/9,DeepSeek9/9,Gemini9/9. 실제총비용$0.1766286997.
rawintent정답7/9,8/9,9/9;04/16/18행위Vpartial1/3,3/3,3/3.
공통실패9→5(14/18/20/21/22),C 최소상황정보기준의정답검토경계남음.
Qwen에intent완성도혼합/V관찰확대/비백엔드CAV감점잔존. 사람이채점할semantic/critical은null.
전체30건성능순위/consistency확정아님. [실험](experiments/2026-09-18_openrouter-policy-recheck.md)참조.

### C 기준 확정 및 Basic 전체 재평가 (2026-09-19)

C는 문제 대상·문제 상태와 증상/조건/영향/비교 중 하나의 연결 여부로 판정하고 원인·행동·검증·직무 적합성을
섞지 않도록 Skill/criteria/dataset v2에 명시했다. case14/18/21/22 C는 partial, case20은 met이다.
관련 평가 테스트 21건과 backend 전체 226건, Python 3.12 mock 30건이 통과했다.

새 기준으로 Basic3종×30건 90회 실행했고 Premium은 호출하지 않았다. 계약 통과는 Qwen24/30,
DeepSeek30/30, Gemini30/30이고 품질 통과/실패/인프라는 각각 14/15/1, 23/7/0, 25/5/0이다.
Qwen case29는 약12분 무응답 후 중복호출 없이 driver watchdog timeout으로 기록해 품질에서 제외했다.
비용 확인89건 합계 $0.5464719216, timeout1건 비용은 미확인이다. 사람 semantic은 전부 null이다.
실행 당시 prompt label은 `coaching-output-v2`이며 본문과 source snapshot에는 새 C 정책이 포함됐다.
[실험](experiments/2026-09-19_openrouter-basic-c-policy-v3.md) 및
`local-results/openrouter-basic-full-c-policy-20260919/REPORT.md` 참조.

### Premium recovery 재평가 (2026-09-19)

최신 Basic 결과 중 DeepSeek 7건·Gemini 5건의 품질 실패 합집합 8건을 중복 제거해 Premium3종을
각 1회, 총24회 측정했다. Qwen은 제외했고 prompt label은 `coaching-output-v3`로 갱신했다.
case20은 known ambiguous로 포함/제외 결과를 함께 저장했다. 전체 복구는 DeepSeek Pro2/8,
Claude2/8, GPT Terra4/8이고 case20 제외 시 2/7, 2/7, 4/7이다. API 인프라 실패는 0이다.
측정24건 비용은 $0.679390498864다. 초기 저장기 오류로 측정 불가 3회가 추가 발생해 해당 비용은
알 수 없으며 품질·복구 지표에서 제외했다. raw/usage/cost/provider는 정식24건 모두 보존했다.
사람 semantic은 null이다. [실험](experiments/2026-09-19_openrouter-premium-recovery-c-policy-v3.md)과
`local-results/openrouter-premium-recovery-c-policy-20260919/REPORT.md` 참조.

### 6종 평가 최종 정리 및 사람 semantic 검토 (2026-09-19)

핵심15case의 Basic45개와 recovery Premium18개, 총63개 출력을 같은 rubric으로 사람이 검토했다.
Batch1만 strict blind였고 이후 batch는 mapping 노출 뒤 채점돼 전체를 완전 blind로 표현하지 않는다.
semantic 집계는 동일 rubric으로 수행한 사용자 제공 사람 검토 결과이며 개별 검토표는 로컬에만 보존한다.
Basic semantic은 DeepSeek91.3%, Gemini90.0%, Qwen68.0%이고 critical은 각각0,0,3건이다.
Premium failure subset semantic은 GPT Terra83.3%, Claude78.3%, DeepSeek Pro73.3%이며 모두 critical0이다.

자동 품질·latency는 Gemini, 비용·semantic은 DeepSeek가 우세해 두 모델을 서로 다른 운영 우선순위의
Basic 후보로 유지한다. GPT Terra는 recovery4/8, 복구당$0.0159, p95 6.09초로 fallback 1순위다.
Qwen은 자동 품질14/29, p95 243.61초와 semantic/critical 결과로 후보에서 제외한다.
Premium semantic은 어려운 subset이므로 Basic과 직접 비교하지 않으며 case20은 known ambiguous다.
최종 근거와 한계는 [평가 리포트](../EVAL_REPORT.md)를 따른다.

### OpenRouter 모델 계열 다양성 평가 (2026-09-21)

현재 키의 인증된 모델 목록 283개 중 text→text/structured output 조건을 만족한 214개를 확인하고,
30개 개발사에서 각 1개를 preflight했다. PASS15개를 고정 dataset v2 30건으로 모두 평가해
450개 고유 사례를 저장했다. 본평가 계약 성공은 모델별 14~30/30이며 Mistral은 rate limit13건이 있었다.
사람 semantic 평가는 수행하지 않았다. 전체 알려진 비용은 $8.2166702564이고 비용 미확인 호출은67개다.
상세 조건·모델별 결과·한계는 [실험 기록](experiments/2026-09-21_openrouter-model-diversity.md)을 따른다.

후속 미평가10개 preflight에서7개가 PASS해210건을 추가 실행했다. Diversity 누적은 preflight40개,
PASS22개, 본평가660건, 알려진 비용$10.2759357145이며 비용 미확인 호출80개다.

동일 조건 Final Four 120건을 별도 실행한 결과 계약은 Flash Lite30/30, Gemini Flash30/30,
GPT Luna29/30, GPT Terra10/30이다. 기계 평가 기준 1차 최종 후보는 Flash Lite와 Luna이며 사람
semantic blind 평가는 아직 미완료다. Final Four runner와 blind CSV 생성·집계 CLI가 추가됐다.
[Final Four 실험](experiments/2026-09-21_openrouter-final-four.md)과 [평가 리포트](../EVAL_REPORT.md)를 따른다.

### PR 크기 정책 및 에이전트 Preflight 검증 개선 (2026-09-21)

- 기존 400 LOC 무조건적 hard limit을 Review Core(코드/테스트/설정/핵심Spec/실험문서) 중심의 가이드라인으로 개선했다.
- Worklog, raw 벤치마크 결과 데이터, lockfile 등 증빙/부수 파일은 Review Core와 분리 계산하며(`docs/experiments/**` 디렉터리 일괄 제외가 아님), 전체 diff가 400줄을 다소 넘는다는 이유만으로 기계적으로 PR을 분할하지 않도록 정책을 명확화했다.
- Review Core가 800줄을 초과하는 경우는 기능/책임 단위 PR 분리를 강제(차단)하고, 400~800줄 구간은 PR description에 사유 및 분리하지 않은 이유를 명시하도록 `scripts/check_pr_policy.py` 및 CI workflow(`.github/workflows/pr-policy-check.yml`)를 추가했다.
- PR description 수정은 더 이상 동일 HEAD에 새 `PR Policy Check` run을 추가하지 않는다. `.github/workflows/pr-policy-rerun-on-edit.yml`이 기존 현재-HEAD run을 자동 rerun하고, 정책 본체는 매 attempt마다 GitHub API에서 최신 PR description을 읽는다. helper는 rerun 직전 현재 PR HEAD를 재확인해 새 commit이 들어왔으면 obsolete rerun을 건너뛴다. policy workflow는 PR+HEAD 단위 concurrency, helper는 PR 단위 concurrency를 사용한다.
- `AGENTS.md` 상단에 6대 필수 수칙을 요약한 `Mandatory Preflight` 섹션을 신설해 작업 착수 전 에이전트가 핵심 규칙을 즉시 인지할 수 있도록 개선했다.
- 중복되던 PR 템플릿을 `.github/PULL_REQUEST_TEMPLATE.md`로 일원화하고, Review-size 분석 항목과 사유 작성을 템플릿에 반영했다.

### 2026-09-23 채팅 공고 검색 출처

- 채팅에서 공고 검색 의도를 해석한 뒤 ALIO·인사혁신처 공공취업정보·재정경제부 공공기관 채용정보를 병렬 조회한다.
- 인천 채용정보는 채팅에서 조회·표시하지 않는다. 인천 백엔드 검색 API와 서버 전용 키 설정은 남아 있지만 채팅 경로에서는 사용하지 않는다.

### 2026-09-23 답변 비교 완료 화면

- 채팅 내 1·2차 답변 비교 결과 아래에 있던 `홈으로 가기`, `처음으로 돌아가기` 완료 메뉴를 제거했다. 비교 결과 표시는 유지한다.

### 2026-09-23 NCS 백엔드 역량 자기점검 채팅

- 로그인 사용자가 연습 채팅을 열면 서버가 `NCS_API_KEY`로 NCS 기준정보 `NCS005`의 응용SW엔지니어링 최신 능력단위를 조회한다. 인증키는 서버에만 있으며 브라우저 응답에 포함되지 않는다.
- 채팅의 코치 메시지는 조회된 능력단위에 연결해 검토한 지식·기술·태도 자기점검 항목을 각 3개씩 표시한다. NCS에는 이 KSA 분류 필드가 없으므로 선택 문구의 작성 주체를 말해봄으로 표시한다.
- 사용자는 여러 항목을 선택해 `선택 완료`로 현재 채팅에 한 번 표시할 수 있다. 선택은 화면 메모리에만 있고 DB·공고 요구사항·답변 평가에는 반영되지 않는다.
- 키 누락, 제공자 오류, 근거 능력단위 누락 시 임의 선택지를 만들지 않고 오류와 재시도를 표시한다. 로그아웃 상태에서는 로그인 안내를 표시한다.
- 백엔드 테스트 250개와 프런트엔드 관련 테스트 28개·production build가 통과했다. 로컬 Docker에서 실제 NCS 조회로 9개 항목과 브라우저 선택·채팅 표시를 확인했다. 외부 배포 환경은 확인하지 않았다.

### 2026-09-23 GitHub README 링크 제출 채팅

- NCS 역량 선택을 완료하면 바로 다음 코치 메시지가 GitHub 저장소 또는 `README.md` 링크를 요청한다. 선택 전에는 이 메시지가 보이지 않는다.
- HTTPS `github.com` 저장소 루트 또는 `README.md` 파일 주소를 확인해 현재 채팅에 클릭 가능한 사용자 메시지로 표시한다. 잘못된 주소는 입력칸 옆에서 수정할 수 있다.
- 이 단계에서는 링크를 현재 화면 메모리에만 유지하고 GitHub 내용 조회·분석은 하지 않았다. 아래 README 분석 후속 구현이 이 상태를 대체한다.
- 프런트엔드 전체 테스트 70개와 production build가 통과했다. 로컬 Docker 브라우저에서 선택 → 링크 요청 → 오류 안내 → 유효한 링크 표시와 스크롤, 콘솔 오류 없음을 확인했다.

### 2026-09-23 GitHub README 기반 Gemini 분석

- 링크를 제출하면 인증된 `POST /api/github/readme/analyze`가 공개 GitHub README 원문을 조회하고 `google/gemini-3.8-flash`로 기술 스택과 프로젝트 기능 흐름을 추출한다. URL은 GitHub 저장소/README 경로로 제한하며 README는 최대 256 KiB다.
- 서버는 구조화된 결과와 항목별 README 원문 근거를 검증하고, 불일치 시 한 번 재시도한다. 채팅은 분석 중 점 3개 입력 표시, 실패 시 재시도·주소 수정, 성공 시 근거 포함 결과를 표시한다. 팀 README만으로 개인의 구현 범위나 숙련도를 확정하지 않는다.
- 조회·분석 결과는 현재 화면에만 표시하며 DB, 공고 요구사항, 코칭 입력에 저장하거나 연결하지 않는다. `OPENROUTER_API_KEY`는 서버에만 둔다.
- 백엔드 격리 환경 전체 257개, 프런트엔드 전체 74개 테스트와 production build가 통과했다. 로컬 Compose에서 제공된 `5Headers/team_project_backend` 주소를 실제로 제출해 GitHub README 조회 → Gemini 응답 → 채팅 표시와 분석 중 입력 표시를 확인했다. 모델이 원문 근거를 두 번 연속 잘못 반환한 한 차례 요청은 실패와 재시도 UI로 처리됐다. 외부 배포 환경과 개별 기여도는 확인하지 않았다.

### 2026-09-23 GitHub README 제출 건너뛰기

- NCS 역량 선택 뒤 나타나는 README 링크 입력에는 `건너뛰기` 버튼도 있다. 누르면 링크 입력을 닫고 건너뛴 선택을 사용자 채팅 메시지로 표시한다. 잘못된 URL 오류가 떠 있어도 건너뛸 수 있다.
- 건너뛰기는 GitHub README 분석 API를 호출하지 않고 현재 화면 상태만 바꾼다. 이제 NCS 선택만 사용한 공고 추천 웹검색을 시작한다. 사용자는 기존 공고 선택과 일반 채팅도 계속 이용할 수 있다. 새로고침하면 이 선택은 초기화된다.
- 프런트엔드 전체 테스트 75개와 production build가 통과했다. 로컬 Compose 브라우저에서 `건너뛰기` 버튼과 선택 후 채팅 표시·입력칸 닫힘을 확인했다.

### 2026-09-23 사람인 웹검색 기반 백엔드 공고 후보

- NCS 선택과 README 분석 완료 또는 README 건너뛰기 뒤 React 채팅이 `POST /api/job-search/recommendations`를 호출한다. 서버는 OpenRouter의 `openrouter:web_search`로 사람인 공고를 검색하고, 사람인 개별 공고 링크만 허용해 원문 페이지에서 제목·기업명·마감일·근거 문구를 다시 확인한다. 키는 서버에만 둔다.
- 검증된 진행 공고 중 선택 NCS 문구와 README 기술·기능 흐름에 닿는 검색 근거가 있는 최대 3건을 표시한다. 검색 엔진의 오래된 결과나 마감 공고는 제외한다. README SHA·인용 문구와 NCS ID를 서버에서 확인한다.
- 2026-09-23 로컬 Compose 브라우저에서 NCS 선택과 지정 README 분석 후 검색 결과 2건이 실제 채팅에 표시됐다. 이후 백엔드 테스트 263개, 프런트엔드 테스트 76개와 빌드가 통과했다. 웹검색 인용과 공고 현황은 호출 시점에 따라 달라질 수 있다.
- 채팅의 사용자 표시 문구는 `공고 검색`으로 통일했다. 검색 상위 서비스가 일시적으로 408·429·5xx를 반환하거나 연결/시간 초과가 나면 서버가 한 번 재시도한다. 그래도 실패하면 출처 이름 없는 오류와 `다시 검색` 버튼을 표시한다.
- 최종 로컬 Compose 화면에서 DNS 장애 중 검색 503을 확인했고, DNS 조회가 복구된 후 같은 화면에서 `POST /api/job-search/recommendations` 200과 공고 카드 1건을 확인했다. 재시도 로직의 503→200 경로는 단위 테스트로 검증했으며, 외부 DNS 장애 중 검색 성공을 보장하지는 않는다.
- 이 결과는 선택 전까지 사용자 확인용 추천 후보이며 검토된 공고 DB·요구사항·코칭 입력에는 자동 연결하지 않는다. 2026-09-23 선택 후 분석·저장 경로는 아래 후속 기록을 따른다. 실제 자격 요건과 접수 상태는 원문에서 다시 확인해야 한다.

### 2026-09-23 잡코리아 추가와 추천 카드 축약

- 웹검색은 사람인과 잡코리아의 개별 공고를 각각 검색하고, URL을 허용 목록으로 제한한 뒤 원문에서 기업·직무·신입 지원 가능 여부·마감일을 다시 확인한다. 한 출처 검색이 실패해도 다른 출처의 확인된 결과는 사용할 수 있다.
- 같은 기업의 같거나 매우 유사한 제목은 점수순으로 한 건만 남긴다. 서로 다른 검증 공고가 있다면 각 출처에서 한 건씩 먼저 포함해 최대 3건을 반환한다.
- 카드에는 회사·직무·경력·마감일, 원문 링크와 실제 겹친 README 항목 최대 하나 및 선택 NCS 항목 최대 하나만 짧게 표시한다. 제출된 README와 일치하는 공고 문구가 없다면 `README 일치 근거 없음`을 표시한다. 원문 발췌와 긴 README 기능 문장은 카드에서 제거했다. 잡코리아의 사이트 로그인 안내가 README 흐름 근거로 잡히지 않도록 본문 범위를 좁혔다. 검색 후보는 여전히 코칭용 검토 공고로 자동 편입되지 않는다.
- 2026-09-23 격리 백엔드 테스트 266개, 프런트엔드 테스트 76개와 production build가 통과했고 로컬 Compose 두 서비스가 healthy였다. 로그인 브라우저에서 지정 README 분석 후 잡코리아 공고 두 건의 간결한 카드를 확인했다. 사람인·잡코리아 각각 진행 중인 개별 공고 원문도 검증했지만, 실제 검색에서 어느 출처가 몇 건 표시되는지는 호출 시점마다 달라진다.

### 2026-09-23 검색 결과 한 건 진단과 후보 보강

- 실제 검색 1회에서 서로 다른 개별 공고 인용 22개 중 원문 확인을 통과한 공고는 4개였다. 검색 인덱스의 오래된 공고와 확인 불가 페이지가 걸러지므로 화면에 표시되는 수는 실행마다 달라진다. 화면 자체는 최대 3건을 표시한다.
- 기본 검색은 이번 달과 다음 달을 모두 대상으로 한다. 원문 검증과 중복 제거 뒤 3건 미만이거나 한 사이트만 남으면 기술·서버 개발 키워드로 보완 웹검색을 수행하고 같은 검증을 적용한다. 확인되지 않은 공고로 수를 채우지 않는다.
- 새 보완 검색 분기까지 격리 백엔드 테스트 269개가 통과했다. 지정된 팀 README의 실제 원문과 `skill-server` 선택으로 실행한 서비스 호출에서 사람인 2건·잡코리아 1건, 총 3건을 반환했다. 첫 공고는 README 기술 `Spring Boot`, `MySQL`과 선택 NCS 항목이 원문과 겹쳤다. 외부 검색 결과는 시점과 검색 제공자 응답에 따라 변동한다.

### 2026-09-23 README 분석 503 복구

- 변경한 OpenRouter 키가 Compose API 컨테이너에 반영됐음을 확인했다. 짧은 Gemini 요청은 200이었으나, 기존 README 구조화 요청은 출력 상한 없이 최대 65,536토큰의 비용을 예약하려 해 OpenRouter에서 402가 발생했다.
- README 분석 출력 상한을 3,072토큰으로 지정하고, 402는 키의 크레딧·사용 한도 문제로 안내한다. GitHub의 일시적인 연결·서버 오류는 한 번 재시도한다.
- README의 `**` 강조·백틱을 제외한 연속 문구도 근거로 인정한다. 모델이 인용한 배지·URL 조합처럼 원문과 맞지 않는 항목은 재요청 뒤 제외하며, 검증된 기술과 흐름이 각각 남은 경우에만 분석 결과를 반환한다. 같은 근거 규칙을 후속 공고 추천의 README 재검증에도 적용했다.
- 전체 격리 백엔드 테스트 275개가 통과했다. 재빌드한 Compose API에서 지정된 공개 README를 실제 `google/gemini-3.8-flash`로 분석해 기술 8개·흐름 4개를 반환했고 API 컨테이너는 healthy였다. 로그인 브라우저 화면에서 `다시 분석` 버튼을 누르는 경로는 다시 조작하지 않았다.

### 2026-09-23 공고 검색 402 진단

- README 분석 성공 뒤 채팅 공고 검색이 두 번 503을 반환했다. API 로그에는 두 출처의 OpenRouter 웹검색에서 모두 402가 기록됐다. 기존 검색 요청에도 출력 상한이 없어 OpenRouter가 최대 65,536토큰 비용으로 계산했다.
- 출처별 검색 요청에 `max_tokens=1536`을 지정하고 짧은 인용 응답을 요청한다. 402가 발생하면 일반 연결 실패 대신 계정 크레딧 또는 키 한도 안내를 보낸다. 한 출처만 실패하고 다른 출처에서 인용을 받았다면 그 인용은 계속 검증한다.
- 한도 적용 후 실제 검색 호출에서 402 없이 응답했으나 인용은 0건이었다. 이어진 외부 호출은 OpenRouter에서 `Insufficient credits. This account never purchased credits`라는 402를 반환했다. 따라서 현 키로 검증된 공고를 반환하는 운영 경로는 아직 확인하지 못했다. 유효 크레딧 확보 뒤 재검증이 필요하다.
- 전체 격리 백엔드 테스트 278개가 통과했다. API 이미지는 변경된 오류 안내까지 다시 빌드해 로컬 Compose에 적용했다.

### 2026-09-23 공고 검색 0건 재현과 보완

- 화면의 빈 결과 요청은 API 200이었다. 실제 재현에서 Google native 기본 검색은 URL citation 0건, 보완 검색은 1건이었으나 공고 원문 검증에서 제외돼 최종 0건이었다. 계정 한도 402와 다른 상황이다.
- 부족한 후보를 위해 OpenRouter Exa 웹검색을 두 채용 사이트 도메인으로 제한해 최대 한 번 추가한다. 반환 URL은 기존 허용 목록과 원문 마감·신입 조건을 통과해야 한다. 실제 추가 검색에서 후보 4건 중 1건이 원문 검증을 통과했다.
- 이 공고의 제목에는 `백엔드 개발자`가 있으나 상세 본문에 관련 키워드가 없어 기존 NCS 겹침 검사에서 빠졌다. 검증한 제목과 본문을 함께 확인하도록 수정했다. 지정 팀 README와 `skill-server` 조건으로 후보 4건을 다시 실제 검색했을 때 잡코리아 공고 1건을 반환했다. README 기술의 직접 일치는 없다고 구분했다.
- 로컬 Compose API를 재빌드했고 검색 관련 테스트 19개가 통과했다. 실제 계정 환경의 전체 백엔드 테스트는 별도 코칭 설정과 충돌해 5개 실패·1개 오류였으며, 코칭 설정·키를 제외한 격리 실행에서는 281개 테스트가 통과했다. 열린 브라우저의 현재 채팅에는 공고 카드 2건이 표시돼 있었지만 API 재빌드 이후 `다시 검색`을 누르지는 않아 그 카드의 생성 시점은 확인하지 않았다. 외부 검색 결과 수는 호출 시점에 따라 달라진다.

### 2026-09-23 추천 공고 선택과 코칭 연결

- 카드에 `공고 선택`을 추가하고 `다시 검색`을 카드 목록과 구분했다. 선택한 공고는 서버가 원문 마감·신입 조건과 상세 내용을 다시 확인한다. 기존 AI 요구사항 분석기의 원문 인용 검증을 통과한 항목만 사용자 소유 `private_job` 검토 공고로 저장한다.
- 검토된 공고는 채팅의 요구사항 1~2개 선택, 질문 유형, 1차 답변·코칭, 2차 답변·비교 화면에 기존 세션 계약으로 연결한다. 검색 응답 자체는 선택 전까지 저장하지 않는다. DB RLS는 다른 사용자의 민간 공고·요구사항·세션 접근을 막는다.
- 빈 기본 검색에서는 출처별 보완 검색보다 Exa 검색을 먼저 수행한다. 검색 경유 URL과 공고 원문 검증을 제한된 수의 병렬 요청으로 처리해 후보별 순차 대기를 줄였다. 실제 외부 검색의 소요 시간과 반환 건수는 네트워크·제공자 응답에 따라 달라진다.
- 관련 단위·통합·DB 정책 검증과 로컬 컨테이너 재빌드 결과는 [작업 기록](worklogs/2026-09-23_1732_private-job-coaching-flow.md)에 남긴다. 실시간 외부 공고 한 건을 사용한 녹음·2차 비교 완주 여부는 별도로 구분한다.

### 2026-09-27 공고 검색 빈 결과·실패 처리 수정

- README 앞 두 기술을 하나의 정확한 문구로 합치지 않고 별도 보완 질의로 사용한다. 마감월의 문자열 형식 일치 요구는 검색어에서 제거했으며 현재 원문의 마감일·신입·백엔드 조건 검증은 유지한다.
- 검색에 reasoning.effort=low를 지정한다. 인용 없는 미완료·null 본문 응답은 한 번 재시도하고, 최종 후보가 없을 때 보완 검색 실패를 정상 빈 결과로 숨기지 않는다. 이미 검증한 공고는 유지한다.
- 관련 테스트 30개와 격리된 backend 전체 테스트 294개가 통과했다. API를 재빌드했으며 웹/API 200과 비인증 검색 401, 컨테이너 healthy, 호스트·실행 코드 해시 일치를 확인했다.
- 제공 README와 skill-server 조건의 실제 서비스 검색은 85.7초 뒤 현재 진행 중인 레데브 공고 1건을 반환했다. README 기술 직접 일치는 없고 NCS 서버 구현 항목과 겹친다. 사용자의 원래 NCS 선택과 로그인 브라우저 재검색 클릭은 확인하지 못했다.
- 원문·URL·근거 검증, 인증, 선택 전 저장 금지와 DB 정책은 유지한다. 자세한 증거·외부 검색 실패·미확인 범위는 [작업 기록](worklogs/2026-09-27_1930_job-search-empty-results.md)에 구분한다.

### 2026-09-28 경력무관 표기·채용 시 마감 공고 허용

- 사람인·잡코리아 원문의 경력 정보를 공백 정규화해 `경력 무관`도 허용하고 검색 질의에 두 표기를 넣는다. `신입 제외`가 명시된 공고는 계속 거부한다.
- 원문 마감일 필드에 `채용 시 마감`이 명시돼 있으면 날짜 없이 허용한다. 필수 응답 필드 `deadline`은 `null`, 카드에는 `채용 시 마감`을 표시한다. 날짜 누락·미정·잘못된 날짜·지난 날짜·마감 안내는 계속 거부하며 공고 선택에도 같은 검증을 적용한다.
- 동일 점수에서 날짜 있는 공고를 먼저 정렬한다. 원문·백엔드 업무·README/NCS 겹침·중복·인증 검사는 유지한다.
- 추천 관련 백엔드 35개, 전체 백엔드 299개, 전체 프런트엔드 79개 테스트와 프런트엔드 빌드가 통과했다. API·웹을 로컬 Compose에 재빌드해 둘 다 healthy, HTTP 200과 비인증 검색 401, 호스트·컨테이너 코드 해시 일치를 확인했다. 실행 API의 두 출처 테스트 원문도 날짜 없이 통과했다.
- 브라우저에서 홈·연습 화면·NCS 목록 표시와 콘솔 오류 없음까지 확인했다. 실시간 외부 공고 검색과 해당 공고 선택·저장은 이번 변경 후 재호출하지 않았다. 검증 범위와 실행 이미지 정보는 [작업 기록](worklogs/2026-09-28_0952_job-search-exceptions.md)에 남긴다.

## 2026-09-28 로컬 변경 이관 7: accept spaced experience labels and explicit until-filled jobs

경력 무관의 공백 변형과 원문 마감 필드의 명시적 채용 시 마감을 허용한다. 종료·경력 제한·누락·미정·잘못된 날짜는 계속 거부하고 날짜를 만들어내지 않는다. 이관 커밋의 검증 결과는 대응 PR과 [작업 기록](worklogs/2026-09-28_pr-series-07-local-job-search-exceptions.md)을 따른다. 원격 통합·운영 배포와 구분한다.

## 2026-10-06 배포 구성 반복 평가 원본 공개

- 현재 운영 트래픽 100% revision의 동일 이미지·Prompt·Skill·30건으로 3회 새 실호출하고 원본·해시·회차별 결과를 공개했다. [반복 평가](evidence/coaching-repeat3-2026-10-06.md). 새 출력 사람 평가·운영 사용자 E2E·배포는 수행하지 않았다.

## 2026-10-06 운영 이력서 기능 GitHub 동기화

- 운영에 있던 PDF 이력서 추출·사용자 확인·건너뛰기와 공고 추천 프로필 연결을 복원했다. 기존 README 및 코칭 모델 설정은 유지한다.
- 관련 검증과 운영 소스/PR 차이는 [Worklog](worklogs/2026-10-06_resume-deployed-github-sync.md)를 따른다.

## 2026-10-06 지원 자료를 코칭에 전달

- 세션에 README 추출·사용자가 확인한 이력서·선택 NCS를 함께 저장하고 기존 MCP 코칭 및 면접 대화에 참고 자료로 전달한다. 실제 답변 근거 검증은 유지한다.
- NCS는 외부 조회 실패 시 같은 instance의 마지막 정상 목록과 조회 시각을 표시한다. 최초 성공 전 또는 재시작 후에는 캐시가 없다.
- [자료 전달 Spec](specs/applicant-context-coaching.md), [NCS Spec](specs/ncs-last-success-fallback.md)를 따른다.
