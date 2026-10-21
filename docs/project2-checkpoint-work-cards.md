# Project2 체크포인트 일정 체크리스트

> 기준일: 2026-09-30
> 기준: 사용자가 2026-09-30 제공한 Checkpoint Project2 `schedule` 탭 D2~D12 캡처
> 범위: D1은 의도적으로 제외한다. 이 문서는 캡처의 날짜별 공식 항목을 임의로 다른 작업으로 대체하지 않는다.
> 현재 상태의 canonical은 [CURRENT_STATE.md](CURRENT_STATE.md), 공식 과제 조건의 canonical은 [REQUIREMENTS.md](REQUIREMENTS.md)다.

## 운영 규칙

- D2~D12의 제목과 항목은 **Checkpoint schedule의 공식 순서를 유지**한다.
- 프로젝트에서 추가로 수행한 모델 비교, Skill 분리, MCP 강화, STT 실험 등은 공식 항목을 밀어내지 않는다.
- 완료는 실제 문서·코드·실행·측정 근거가 있을 때만 `[x]`로 표시한다.
- 기반은 있으나 캡처가 요구하는 증거가 덜 갖춰졌으면 `[-]`로 표시하고 남은 것을 한 줄로 적는다.
- 아직 수행하지 않았거나 검증 근거가 없으면 `[ ]`로 둔다.
- 상태가 바뀌면 같은 변경에서 이 문서와 관련 Worklog를 함께 갱신한다.
- 날짜가 지났더라도 빠진 항목은 이후 날짜의 다른 작업으로 덮지 않고 원래 Day에 남겨 추적한다.

## 상태 표기

- [x] 완료 또는 현재 저장소에서 검증 완료
- [ ] 미완료 또는 추가 검증 필요
- [-] 일부 완료 / 기반 구현은 있으나 체크포인트 관점의 증거가 부족함

## 현재 진행상황 요약

| 영역 | 상태 | 현재까지 확인된 내용 / 남은 것 |
| --- | --- | --- |
| 로컬 제품 E2E | [x] | 근거: `docs/CURRENT_STATE.md`, `docs/experiments/2026-09-21_service-candidate-integration.md` |
| Agent API | [x] | 근거: `docs/CURRENT_STATE.md`, 기본 질문 1~10 코칭 및 비교 후 면접 대화 API/UI 구현 |
| Skill 분리 | [x] | 근거: `skills/github-readme-evidence/SKILL.md`, `skills/job-requirement-extraction/SKILL.md`, `skills/interview-coach/preset-interview.md` |
| MCP | [x] | 실제 stdio MCP 호출, 권한 경계, 로그인 사용자 Compose의 MCP 장애 503·`mcp_error`·재시도 안내까지 검증 |
| Langfuse | [-] | 실제 provider 성공/실패·retry trace는 로컬 사용자 흐름에서 확인. 남음: production trace, Prompt production 승격/rollback, D11 동일 Dataset 재평가 |
| Prompt / 평가 | [x] | 근거: `EVAL_REPORT.md`, `docs/CURRENT_STATE.md` |
| Docker | [x] | 근거: `docs/CURRENT_STATE.md`의 전체 E2E 및 backend 274 tests 기록 |
| 배포 | [x] | 2026-10-06 공개 Frontend·Cloud Run `/health`·Frontend Origin CORS를 재검증했고 README에 운영 주소를 명시함. 로그인 사용자 전체 E2E와 production trace는 별도 항목에서 추적 |
| 최종 제출 문서 | [-] | 남음: 최종 Evidence loop·known issue·Langfuse 캡처·데모 영상 정리 |
| STT 실제 사용자 평가 | [-] | 1인 30건 devset의 raw/정규화 CER·WER, 9조합 모델×beam, prompt A/B, CPU/GPU 비교 및 파인튜닝 holdout은 완료. 남음: 신규 다중 화자 독립 acceptance·운영 Hosted E2E·최종 모델 결정 |
- [x] 완료 / 검증 근거 있음
- [-] 일부 완료 / 기반은 있으나 공식 항목의 증거가 부족함
- [ ] 미완료 / 검증 필요

> `(강사 확인 종료)` 표시는 실제 수행 증거를 새로 확보했다는 뜻이 아니다. 사용자 전달 기준 강사님 별도 컨펌으로 해당 추가 증빙·재검증 요구를 더 이상 추적하지 않는 항목을 구분한다.

## 현재 요약

| Day | 공식 주제 | 현재 상태 | 핵심 남은 것 |
| --- | --- | --- | --- |
| D2 | 문제 정의서 · 범위 제외 | 완료 (강사 확인) | 경쟁 서비스 3개 직접 사용 메모 추가 증빙은 강사 별도 컨펌으로 종료 |
| D3 | 출력 계약 · 관측 규칙 | 완료 | 신뢰 경계와 활성 도메인 source의 이용조건 등록부까지 정리 |
| D4 | 평가셋 30건 확정 | 완료 | 30건 사람 검토 완료, case별 판정자·근거 및 V 보조지표 기록 |
| D5 | 세로 슬라이스 기둥 | 완료 (강사 확인) | 기술 산출물 완료, blocker standup 및 비교→면접 대화→종료 추가 검증은 강사 별도 컨펌으로 종료 |
| D6 | 실제 LLM 호출 · 실패 경로 · trace | 완료 | 실제 provider·실패/retry·redacted input/output·지연 trace 확인 |
| D7 | 무엇을 버릴지 결정 | 완료 (강사 확인) | 발표용 중간 점검 1장 작성 완료. 10/7 실제 시연·문서 확인 과정에서 강사가 현재 시연/문서 수준을 확인했고 팀은 추가 중간점검 발표를 진행하지 않기로 정리 |
| D8 | 누구나 재현 가능한 실행 절차 | 완료 | clean clone·README·health·인증 최소 사용자 흐름 검증 완료. 운영 환경 차이는 D10에서 검증 |
| D9 | Skill · MCP 연결 | 완료 | Skill·MCP 호출·권한 정책·로그인 사용자 MCP 장애 경로까지 검증 완료 |
| D10 | 배포 URL · prompt v1 | 일부 완료 | 공개 배포 URL 검증 완료. 남음: 같은 운영 실행의 production trace, 강사 판정과 현재 배포 증거 정합성, managed Prompt release/rollback |
| D11 | baseline 측정 · 개선 가설 | 일부 완료 | 운영 이미지 30건×3회 baseline·약점 확인 및 단일 Skill 규칙 smoke 완료. 남음: 신규 인젝션 3건 독립 사람 확정·동일 조건 before/after와 사람 품질 검토 |
| D12 | 전후 재측정 · 코드 동결 | 미완료 | 최종 재측정·코드 동결은 기술 검증으로 유지. 내일 회의자료·시연 준비는 곽호준 담당으로 분리 |

### 2026-10-07 팀 합의 — 최종 회의/시연 자료 담당 분리

- [x] **D7 추가 발표 작업 종료** — 10/7 강사 확인을 기준으로 중간점검 발표를 별도로 반복하지 않는다.
- [-] **내일 회의자료·시연 준비 담당 분리** — 곽호준이 회의자료를 별도로 준비해 다음 회의에 참여하기로 했다. 이 담당 이관은 발표 준비 중복을 줄이기 위한 팀 합의이며 D12의 기술 검증 완료를 의미하지 않는다.
- 기술 검증 담당의 우선순위는 D11 인젝션 before/after·Prompt+Skill 사람 품질 검토·PlayMCP 동일 요청 trace·운영 배포/production trace 정합성·managed Prompt release/rollback·최종 재측정·코드 동결로 유지한다.
- 정상/실패 데모 영상과 Langfuse 상세 캡처는 실제 파일/제출 근거가 확인될 때 각각 `[x]`로 전환한다.

---

## D2 · 9/21 — 기획 · 문제 정의서 · 범위 제외

- [x] **문제 정의서 1장 — 사용자, 상황, 핵심 작업, 성공 기준**
  근거: `docs/product/problem-definition.md`, `docs/PROJECT_OVERVIEW.md`
- [x] **하지 않을 일을 먼저 적는다 — 뺄 것을 정하지 않으면 2주에 안 끝난다**
  근거: `docs/product/problem-definition.md`, `docs/CONSTRAINTS.md`
- [x] **LLM과 코드 역할 분리표 — 업무별로 무엇을 LLM이 판단하고 무엇을 코드가 결정하는지**
  근거: `docs/product/problem-definition.md`, `docs/ARCHITECTURE.md`, `AGENTS.md`
- [x] **경쟁 조사 — 같은 질문에 답하는 기존 서비스 3개를 직접 써보고 부족한 점을 기록한다** *(강사 확인 종료)*
  근거: `docs/product/differentiation-strategy.md`에 공개 자료 기반 경쟁 분석이 있음
  처리: 사용자 전달 기준, 강사님 별도 컨펌으로 **3개 서비스 직접 사용 결과와 부족한 점의 추가 제출·증빙은 더 이상 추적하지 않는다.** 저장소에는 실제 직접 사용을 수행했다는 근거를 새로 만들지 않는다.
- [x] **조 저장소 README에 한 문장 정의 기입 — 무엇을 하는 서비스인가**
  근거: 루트 `README.md` 3~4행에 말해봄 Mk.2의 사용자·행동·목적을 한 문장으로 정의

**남길 것:** 문제 정의서 1장 · 하지 않을 일 목록 · 경쟁 조사 메모

---

## D3 · 9/22 — 설계 · 출력 계약 · 관측 규칙

- [x] **입출력 Pydantic 스키마 확정 — 성공 응답과 실패 응답의 형태**
  근거: `backend/app/schemas/coaching.py`, `docs/specs/coaching-output-contract.md`, `docs/REQUIREMENTS.md`
- [x] **실패 상태 정의 — 정보 부족, 범위 밖, 도구 실패를 각각 어떤 상태로 낼지 정한다**
  근거: `docs/REQUIREMENTS.md`, `backend/app/services/coaching_runtime.py`, 출력 계약 테스트
- [x] **Langfuse observation 속성과 프롬프트 버전 이름 규칙 합의**
  근거: `backend/app/services/coaching_prompt.py`, `docs/CURRENT_STATE.md`의 trace/model/token/cost/latency/retry 및 Prompt version 기록
- [x] **신뢰 경계 1장 — 사용자 입력, 외부에서 가져온 데이터, 도구가 돌려준 값 중 무엇을 믿지 않을지 정한다**
  근거: `docs/TRUST_BOUNDARY.md`에 사용자 입력·외부 source·MCP 반환값·LLM 출력·관측·secret의 신뢰 수준과 검증/실패 정책을 한 장으로 고정
- [x] **API 엔드포인트 목록 확정 — 프론트가 부르는 것과 LLM이 도구로 부르는 것을 구분한다**
  근거: `docs/ARCHITECTURE.md`, `docs/REQUIREMENTS.md`, `README.md`
- [x] **도메인 지식 출처 정리 — 공개 API·문서·사람 중 어디서 오는지, 라이선스 확인한다**
  근거: `docs/research/DOMAIN_SOURCE_REGISTER.md`에 NCS·공공채용 API·ALIO·민간 공고·GitHub README·사람 검토의 출처 유형, 사용 위치, 이용허락/약관 상태와 보수적 저장 정책을 기록

**남길 것:** Pydantic 스키마 · 실패 상태 표 · 관측/프롬프트 버전 규칙

---

## D4 · 9/23 — 설계 · 평가셋 30건 확정

- [x] **평가셋 30건 확정 — 정상·경계·실패를 섞는다**
  근거: `evals/dataset.v2.jsonl`, `EVAL_REPORT.md`
- [x] **경계 문항은 도메인 판정을 요구하게 만든다 — 정책 문항만으로 채우지 않는다**
  근거: `evals/dataset.v2.jsonl`의 경계 10건은 문제 맥락·개인 행동·결과 검증·직무 관련성 등 실제 답변의 C/A/V 판정을 요구하며 단순 문자열/정책 확인으로 구성되지 않음
- [x] **문항마다 판정자 이름과 판정 근거 한 줄을 적는다**
  근거: `evals/reviewer-assignment.md`에서 김재훈이 30건 전체를 검토해 29건은 기존 판정을 확정하고, `coach-boundary-17`의 V는 `partial → undetermined`로 수정 확정했다. 각 case에 최종 근거 한 줄과 V 보조지표를 기록했으며 단일 검토라 검토자 간 일치도는 측정하지 않았다.
- [x] **점수 기준(rubric)과 baseline 기록 양식 확정**
  근거: `evals/README.md`, `EVAL_REPORT.md`
- [x] **연휴 전 결정 재확인 — 연휴가 끝난 뒤 다시 논의하지 않을 것들을 못 박는다**
  근거: `docs/CONSTRAINTS.md`, `docs/DECISIONS.md`, `docs/PROJECT_OVERVIEW.md`

**남길 것:** `evals/dataset.jsonl` 30건 · score rubric · 판정자 배정표

> 현재 실제 canonical dataset은 `evals/dataset.v2.jsonl`이다. 캡처의 산출물 명칭과 실제 파일명을 혼동하지 않는다.

---

## D5 · 9/28 — 빌드 · 세로 슬라이스 기둥

- [x] **세로 슬라이스 — FastAPI 엔드포인트가 계약된 입력을 받아 mock 응답까지 반환한다**
  근거: 현재 `POST /api/agent`는 mock 단계를 넘어 실제 provider·검증·저장까지 연결됨. `docs/CURRENT_STATE.md`
- [x] **`docker compose up`으로 로컬에서 기동된다**
  근거: 로컬 Docker + Supabase 전체 E2E 및 Compose 검증 기록. `docs/CURRENT_STATE.md`
- [x] **프롬프트 v0 작성 — 시스템 프롬프트와 출력 지시**
  근거: 초기 Prompt를 거쳐 현재 사용자 제공 코칭 시스템 Prompt와 Skill 조립을 `backend/app/services/coaching_prompt.py`에 적용. 최신 기본 버전과 실험용 과거 버전의 구분은 `docs/CURRENT_STATE.md`를 따른다.
- [x] **저장소 구조 확정 — `backend/`, `evals/`, `SKILL.md` 뼈대**
  근거: `backend/`, `evals/`, `skills/interview-coach/SKILL.md`
- [x] **매일 15분 스탠드업 시작 — 진행 보고가 아니라 막힌 것만 말한다** *(강사 확인 종료)*
  처리: 코드·문서 산출물이 아닌 팀 운영 항목이다. 사용자 전달 기준, 강사님 별도 컨펌으로 **실제 운영 근거의 추가 제출·확인은 종료**한다. 저장소에는 standup 실제 시행 기록이 새로 확인된 것으로 적지 않는다.

- [x] GitHub README 근거 분석을 공통 analysis skill 경로로 분리 — 근거: `skills/github-readme-evidence/SKILL.md`, `backend/app/services/analysis_skill.py`
- [x] 공고 요구사항 추출을 별도 skill로 분리 — 근거: `skills/job-requirement-extraction/SKILL.md`, `backend/app/services/alio_requirement_analysis.py`
- [x] 기본 질문 1~10을 질문별 context / 활성 기준 / preset skill에 연결 — 근거: `skills/interview-coach/preset-interview.md`, `backend/app/services/coaching_questions.py`, `docs/CURRENT_STATE.md`
- [x] 비교 후 면접 대화 service / API / UI / 종료 동선 연결 *(강사 확인 종료)* — 구현·회귀 테스트 근거는 기존 문서에 유지하며, 사용자 전달 기준 강사님 별도 컨펌으로 **비교 완료 → 면접 대화 → 종료 로그인 사용자 E2E의 추가 재검증은 더 이상 추적하지 않는다.**
- [x] 공통 JSON LLM provider를 OpenAI SDK 호출 경로로 통합 — 근거: `backend/app/services/coaching_runtime.py`, `docs/CURRENT_STATE.md`
**남길 것:** FastAPI 골격 · `docker-compose.yml` · 프롬프트 v0

---

## D6 · 9/29 — 빌드 · 실제 LLM 호출 · 실패 경로 · trace

- [x] **실제 LLM 호출 연결 — mock을 걷어낸다**
  근거: 실제 OpenRouter Flash-Lite 호출 및 로그인 사용자 E2E. `docs/CURRENT_STATE.md`
- [x] **검증·재시도·사용자용 실패 응답 경로를 코드에 넣는다**
  근거: 출력 계약 검증/repair, provider retry/timeout, 최종 실패 응답. `docs/CURRENT_STATE.md`
- [x] **Langfuse trace 연결 — 입력·출력·지연이 실제로 남는지 확인한다**
  근거: 9/29 실제 provider 3건에서 `coaching.analyze` / `coaching.provider` / `coaching.output_validation`을 같은 trace로 확인했고 provider Duration 3.892s / 3.206s / 2.666s, token·cost를 기록했다. 실제 로그인 사용자 흐름에서도 성공 trace와 controlled network failure의 retry attempt 1→2를 Langfuse Cloud에서 확인했다. `backend/app/services/coaching_observability.py`는 개인정보 보호를 위해 provider generation의 input/output을 `content_policy=redacted` 구조 정보로 기록하며 테스트가 이를 고정한다. 근거: `[REDACTED].md`, `[REDACTED].md`, `backend/tests/test_coaching_observability.py`
- [x] **출력 파싱 실패 시 동작 결정 — 재시도 횟수와 폴백을 정한다**
  근거: JSON/Pydantic/서버 계약 실패 시 repair 포함 최대 시도 횟수와 최종 실패 경로 구현. `backend/app/services/coaching_runtime.py`, `docs/CURRENT_STATE.md`
- [x] **데이터 출처 태깅 — 외부에서 온 내용과 시스템 지시를 프롬프트에서 분리한다**
  근거: canonical system prompt가 질문·답변·공고·MCP 반환값 내부 지시를 “분석 대상 데이터”로 명시하고 서버가 제공한 ID만 사용하도록 제한. `backend/app/services/coaching_prompt.py`
- [x] **에러 로깅 — 어디서 무엇이 실패했는지 남는가**
  근거: provider network retry, output validation, persistence 실패를 분리한 Langfuse/Worklog 증거. `docs/CURRENT_STATE.md`

**남길 것:** LLM 호출 코드 · 실패 응답 경로 · Langfuse trace 화면

### D6에서 공식 항목보다 먼저 진행한 추가 작업

- 실제 로그인 사용자 normal / boundary / injection 3종 E2E 완료
- 1차 답변 → 코칭 → 2차 답변 → 비교 E2E 완료
- 인증된 HTTP `/mcp`, capability token, 도메인 도구, transport 테스트 구현
- 실제 provider 성공/실패 Langfuse trace와 token/cost/latency/retry metadata 확인

이 항목들은 진행 근거로 활용하되 D6 공식 항목을 대체하지 않는다.

---

## D7 · 9/30 — 빌드 · 무엇을 버릴지 결정

- [x] **무엇을 버릴지 결정한다 — 남은 5 작업일에 못 할 것을 뺀다**
  근거: 기존 제외 범위는 `docs/CONSTRAINTS.md`에 있으며, 2026-10-01에 확인한 9/30 중간점검 문서에서 추가 음성 학습·대형 모델 전환·장기 기억을 이번 제출에서 보류한다고 고정. 외부 근거의 URL·Page ID·확인 범위는 `docs/worklogs/2026-10-01_d7-checkpoint-refresh.md`에 기록
- [x] **문제 정의와 평가셋 재확인 — 구현하다 보면 원래 문제에서 멀어진다**
  근거: 신입 백엔드의 문제 해결 답변, 공고 1개·요구사항 1~2개, 근거 코칭·재답변 비교를 현재 핵심 범위로 재확인했고 Dataset v2 30건의 사람 검토도 완료
- [x] **아키텍처 재점검 — 지금 구조로 남은 5 작업일에 배포까지 갈 수 있는지 확인한다**
  근거: 2026-10-01에 확인한 9/30 중간점검 문서에서 기획/도메인, Backend/MCP/공고, LLM/Skill, 화면/STT, 관측/Docker/배포, 최종 제출 준비를 영역별로 재점검하고 각 영역의 남은 작업을 기록. 확인 범위는 `docs/worklogs/2026-10-01_d7-checkpoint-refresh.md`
- [x] **baseline 1차 측정 — 30건 중 몇 건이 통과하는지 숫자로 본다**
  근거: 2026-10-01에 확인한 `baseline 1차 측정` 문서의 상단 비교표에서 D7 기준 최신 실행을 자동 전체 통과 **23/30**, 정상 **12/12**, 경계 **5/10**, 실패 유도 **6/8**, p95 **5.54초**, 30건 비용 **$0.2151**로 기록. Notion URL·Page ID·확인 범위와 수치 snapshot은 `docs/worklogs/2026-10-01_d7-checkpoint-refresh.md`
  비고: 첫 실행 19/30과 최신 실행 23/30은 단일 호출 → 사실 추출 후 최종 판정 2단계 구조로 바뀌어 Prompt 문구만의 순수 A/B가 아니다. 같은 문서 후반의 9/30 strict JSON Schema 별도 실행 20/30(정상 10/12, 경계 3/10, 실패 유도 7/8)은 별도 측정으로 구분한다.
- [x] **중간 점검 1장 작성·강사 확인 — 별도 장표 발표는 추가 진행하지 않는다**
  근거: 2026-10-01에 확인한 `baseline 1차 측정` 문서에 문제 정의·평가셋·아키텍처·baseline·제외 범위·남은 5일 계획을 통합. 확인 범위는 `docs/worklogs/2026-10-01_d7-checkpoint-refresh.md`
  작성: `docs/D7_INTERIM_CHECKPOINT_ONE_PAGE.md`에 발표용 한 장 형식으로 압축 완료
  추가 확인(10/7 팀 공유): 곽호준이 회의자료를 준비해 실제 시연을 진행했고 문서도 보여드리려 했으나, 강사가 현재 시연 퀄리티와 문서 수준이면 괜찮다고 확인해 별도 장표 발표는 진행하지 않았다. 팀 합의에 따라 D7은 강사 확인 완료로 종료한다. 별도 업로드/제출 영수증을 확보했다는 의미는 아니다.

**남길 것:** 발표용 중간 점검 1장 artifact · 10/7 강사 확인에 따른 종료 기록

---

## D7 · 9/30 — 중간 체크포인트 준비 및 상태 고정

- [x] 문제 정의 — 근거: `docs/product/problem-definition.md`
- [x] 핵심 사용자와 MVP 범위 — 근거: `docs/PROJECT_OVERVIEW.md`
- [x] Agent가 판단하는 대상 정의 — 근거: `docs/PROJECT_OVERVIEW.md`, `skills/interview-coach/SKILL.md`, `skills/github-readme-evidence/SKILL.md`, `skills/job-requirement-extraction/SKILL.md`, `skills/interview-coach/preset-interview.md`
- [x] LLM과 코드의 역할 분리 — 근거: `docs/ARCHITECTURE.md`, `backend/app/services/analysis_skill.py`, `backend/app/services/coaching_runtime.py`
- [x] 평가셋 및 출력 계약 존재 — 근거: `evals/`, `EVAL_REPORT.md`
- [x] 로컬 아키텍처와 주요 호출 경로 문서 존재 — 근거: `docs/ARCHITECTURE.md`, `docs/CURRENT_STATE.md`
- [x] 현재 아키텍처를 중간 점검용 한 장 설명으로 정리 — 근거: `docs/D7_INTERIM_CHECKPOINT_ONE_PAGE.md`에 문제 정의·평가셋·아키텍처·baseline·제외 범위·남은 일정을 한 장으로 압축
- [x] 도메인 지식 출처와 사용 위치 재확인 — 근거: 2026-10-01에 확인한 `출력 파싱과 데이터 출처 및 에러 로깅` 문서에서 system 규칙, 질문, 답변, 공고, 보정 요청, 반환 근거의 전달 위치와 source 필드를 구분하고, 중간점검 문서에서 공고/NCS/MCP 사용 위치를 재확인. URL·Page ID·확인 범위: `docs/worklogs/2026-10-01_d7-checkpoint-refresh.md`
- [x] 평가셋 / 판정 기준 요약 — 근거: 2026-10-01에 확인한 `baseline 1차 측정` 문서에 30건 baseline, 정상/경계/실패 유도별 통과 수, latency·비용, 비교 한계를 함께 기록. 수치 snapshot과 비교 한계: `docs/worklogs/2026-10-01_d7-checkpoint-refresh.md`
- [x] 현재 구현 상태와 남은 필수 범위 요약 — 근거: `docs/CURRENT_STATE.md`, 본 체크리스트의 완료/부분 완료/미완료 상태
- [x] 문서 간 충돌 여부 최종 확인 — 근거: PR #140에서 공고 원문 분석을 미래 기능으로 표현하던 현재 제품 문서를 구현 범위에 맞췄고, `docs/README.md`의 동일한 stale 설명도 현재 흐름으로 정리. 과거 Worklog는 당시 snapshot이므로 보존
- [x] 이후 일정에서 할 일과 하지 않을 일 고정 — 근거: 남은 5일을 핵심 흐름 수정 → Skill/판정 평가 → 배포·MCP 검증 → 제3자 재현·증거 확보 → 오류 수정·최종 문서화로 고정하고, 추가 음성 학습·대형 모델·장기 기억은 보류. 확인 snapshot: `docs/worklogs/2026-10-01_d7-checkpoint-refresh.md`

---

## D8 · 10/1 — 프로덕션 · 누구나 재현 가능한 실행 절차

- [x] **최소 사용자 흐름 완성 — 입력부터 결과까지 끊기지 않는다**
  근거: 로그인 → 공고 → 세션 → 음성 분석 → 코칭 → 저장 및 1·2차 비교 로컬 E2E. `docs/CURRENT_STATE.md`
- [x] **README 실행 절차 — 다른 사람이 clone 후 그대로 돌릴 수 있는가**
  근거: 빈 환경 clean clone → `.env.example` 기반 설정 → `docker compose up --build` → `/health` 200 → 실제 코칭 흐름과 Mock E2E 종료 코드 0을 확인. `docs/worklogs/2026-09-30_1425_d8-clean-clone-verification.md`
  2026-10-10 추가 점검: 위 완료 표시는 9/30 당시 검증이다. 현재 main 새 clone의 ARM64 최초 빌드는 10분 기준을 넘겼고 기동 확인 전에 중단했다. CPU 의존성 개선 및 현재 구성 재검증 필요. [재현 점검](evidence/clean-compose-reproduction-20261010.md)
  CPU 이미지 개선 후 새 clone 후보는 6분 34.86초 healthy 및 실제 소개/연습 표시를 확인했다. 캐시된 같은 공개 모델로 합성 WAV STT/VAD도 통과했다. 첫 모델 다운로드와 인증·DB·코칭 전체 흐름을 새로 검증한 것은 아니다. [CPU 재현 점검](evidence/local-cpu-reproduction-20261010.md)
- [x] **health check 엔드포인트**
  근거: `GET /health`, Docker healthcheck. `backend/app/main.py`, `docker-compose.yml`
- [x] **프롬프트 v1 등록 — Langfuse prompt management**
  근거: Langfuse candidate Prompt version 1 등록 기록. `docs/CURRENT_STATE.md`
- [x] **`SKILL.md` 착수 — 도메인 규칙 초안을 문서로 옮기기 시작한다**
  근거: `skills/interview-coach/SKILL.md`, `skills/interview-coach/preset-interview.md`, 분석 Skill 파일들

**남길 것:** README 실행 절차 · `/health` · prompt v1 등록

### 운영 배포 준비 체크 — D10 선행 준비

> 아래 항목은 D8 완료 판정과 별개이며 D10의 실제 외부 배포 검증으로 이어진다.

- [x] 현재 Frontend 배포 상태 확인 — 공개 주소 `https://www.malhaebom.xyz/` 외부 GET 200 및 배포 JS에서 Cloud Run API 호스트 연결 확인. 사용자는 운영 브라우저에서 로그인 후 공고 검색·원문 분석·1/2차 비교까지 성공했다고 직접 보고했다. 운영 요청 로그·실행 캡처·현재 리비전의 별도 검증은 D10 증거 과제로 유지한다. [증거 점검](experiments/2026-10-02_evaluation-evidence-gap-audit.md)
- [x] 환경변수 정리 — README에 실제 최소 사용자 흐름용 Supabase·OpenRouter·MCP 환경변수, 공개/서버 전용 구분, `.env` 보관 원칙과 `VITE_*` 배포 동작을 정리했다.
- [x] 운영 API endpoint 연결 준비 — 배포 Frontend JS의 Cloud Run API 주소 확인, 운영 API `/health` 200 및 CORS OPTIONS 200 확인. 사용자 운영 브라우저에서 공고 검색·원문 분석·1/2차 비교까지 성공 보고. 현재 리비전의 서버측 PlayMCP 호출 로그는 별도 미확인
- [ ] 브라우저에 secret이 노출되지 않는지 확인 — 코드·문서상 서버 전용 secret은 분리돼 있다. 남음: 실제 배포 JS bundle/Network 기준으로 서버 secret 문자열 미노출을 별도 검사.

### Cloud Run

- [x] Backend container 운영 빌드 확인 — 10/6 배포 pin에 immutable image digest와 `malhaebom-mk2-resume-1004-1438` revision을 고정했고 동일 배포 이미지에서 30건×3회 provider 평가를 실행했다.
- [x] Cloud Run 서비스 생성/업데이트 — `malhaebom-mk2-resume-1004-1438` revision에 트래픽 100%를 확인했고 공개 `/health`가 HTTP 200을 반환했다.
- [-] 운영 환경변수 / secret 설정 — 운영 로그인·외부 provider 호출·Langfuse trace가 실제 동작해 필수 설정의 존재는 확인했다. 남음: secret 값을 노출하지 않는 방식으로 현재 revision의 설정 항목·권한 구성을 대조해 증거화.
- [x] Supabase 운영 인증 설정 확인 — 사용자가 운영 브라우저에서 실제 로그인 후 공고 검색·원문 분석·연습·1/2차 비교까지 성공했다고 확인했다. RLS/세부 권한 증거는 운영 환경 차이 항목에서 별도 추적한다.
- [x] Langfuse 운영 설정 확인 — 운영 사용자 흐름 이후 Langfuse Cloud에 `coaching.provider → coaching.output_validation → coaching.analyze` trace가 남은 것을 확인했다. 정확한 revision·Prompt/Skill 버전 연결은 D10에서 계속 추적한다.
- [x] 외부 provider 설정 확인 — 배포 pin에 `openai_compatible` / Gemini 3.5 Flash-Lite / OpenRouter base URL을 기록했고 동일 배포 이미지의 90실행에서 실제 provider 호출을 확인했다.

### 문서

- [x] 빈 환경 clean clone에서 README 절차로 로컬 Mock 계약 E2E와 인증된 실제 최소 사용자 흐름 검증 — `health` 200, 분석 작업 조회 200, 전사 revision 201, 코칭 200, Mock E2E 종료 코드 0을 확인. 근거: `README.md`, `docs/worklogs/2026-09-30_1425_d8-clean-clone-verification.md`
- [-] 로컬과 운영 환경 차이 기록 — 로컬 기본 포트·필수/선택 환경 변수는 README에 기록했고 운영 Frontend 외부 GET 200, 배포 JS의 Cloud Run API 호스트 및 운영 API `/health` GET 200을 확인했다. 남음: 실행 리비전·운영 secret 구성과 인증 후 전체 흐름의 권한 기반 검증. [증거 점검](experiments/2026-10-02_evaluation-evidence-gap-audit.md)
- [-] 로컬 Mock 계약 E2E와 인증된 실제 최소 사용자 흐름을 README에 반영·검증 — 남음: Vercel/Cloud Run 운영 URL·환경 차이의 실제 검증. Langfuse trace는 이번 검증 범위에서 제외. 근거: `README.md`, `[REDACTED].md`

---

## D9 · 10/2 — 프로덕션 · Skill · MCP 연결

2026-10-09 재점검: 운영 Prompt와 Skill의 met 조건 차이를 확인하고 별도 후보 및 100개 정합성/회귀 테스트를 작성했다. [Worklog](worklogs/2026-10-09_deployed-skill-met-alignment.md). 후보 PR이며 운영 승격·실제 LLM 재평가는 미실행이므로 D10/D11 상태는 유지한다.

- [x] **MCP 서버 구현 — `@mcp.tool()`로 도메인 도구를 정의한다**
  근거: `mcp_server/server.py`의 FastMCP 도구들
- [x] **`SKILL.md` 확정 — D8에서 시작한 도메인 규칙 문서를 완성한다. 뼈대만 남아 있으면 미충족이다**
  근거: `skills/interview-coach/SKILL.md`, `skills/interview-coach/preset-interview.md`, versioned analysis Skills
- [x] **서비스에서 MCP 도구가 실제로 호출되는지 확인한다**
  근거: FastAPI → stdio FastMCP context gateway 및 로그인 사용자 E2E. `backend/app/services/mcp_context_gateway.py`, `docs/CURRENT_STATE.md`
- [x] **도구 권한 정책 — 부작용 도구를 구분하고 명시적 요청·권한 없이 쓰기 도구를 호출하지 않게 한다. 도구의 이름·설명·반환값도 신뢰하지 않는다**
  근거: 현재 MCP는 제한된 읽기 도구만 제공하고 capability token의 사용자·scope·허용 ID·만료를 검증. 반환 문맥은 server contract와 LLM 출력 검증을 다시 통과
- [x] **도구 호출이 실패할 때의 동작 확인**
  근거: 로그인 사용자 로컬 Compose 흐름에서 존재하지 않는 MCP 서버 경로를 주입했다. 답변 revision 저장 뒤 `/api/agent`가 `503`, `mcp_error`, `COACHING_MCP_UNAVAILABLE`, `retryable=true`을 반환하고 화면의 재시도 안내와 API 로그의 `failure_stage=context`를 확인했다. [Worklog](worklogs/2026-10-01_0945_d9-mcp-failure-contract.md), [재실행 절차](dev/d9-mcp-failure-e2e.md)

**남길 것:** `SKILL.md` · `@mcp.tool()` 도구 · 호출 로그

---

## D10 · 10/6 — 프로덕션 · 배포 URL · prompt v1

- [x] **소개 페이지를 서비스 도메인의 첫 화면으로 연결**
  10/10 운영 반영: 양쪽 기존 도메인 소개 `/` → 연습 시작 `/app/practice`, 서비스 홈 `/app/` 유지. 279 tests/build와 실제 운영 브라우저의 기존 로그인 상태 채팅 연결·공개 HTML/asset 일치를 확인했다. main 실행 소스와 Cloud Run도 동기화했다. [Worklog](worklogs/2026-10-10_serving-source-main-sync.md). 신규 Google OAuth 완료·실녹음 전체 E2E는 별도 미검증이며 마감 전 제출 증거로 소급하지 않는다.

**10/8 후속 운영 관측 (비식별):** 사용자가 제공한 Langfuse `malhaebom-coaching-v5-reinforced-verification` 관리 화면에서 **숫자 버전 #4에 `production`·`latest` 라벨**을 확인했다. 해당 버전의 Linked Generations에서 **10/8 12:38:46 코칭 호출이 이전 Tracing 캡처와 동일 trace ID**임을 대조했고, provider `version=malhaebom-coaching-v5-reinforced-verification@4`·`google/gemini-3.5-flash-lite`·HTTP 200·재시도 없음·8.19초·$0.006809를 확인했다. 같은 trace `coaching.output_validation`의 **`CoachingLLMOutput` 계약은 `valid=true`, `error_count=0`**이었다. `skill_version=interview-coach-v6` 표시는 provider와 validation에 공통이나, **실제 로딩한 Skill 번들**은 아직 검증되지 않았다. 따라서 **Prompt 연결 및 이 요청의 출력 계약 검증 증거는 확보**, 운영 Cloud Run revision/DB/PlayMCP 동일 요청 연계와 release/rollback 실증은 미완료로 유지한다. [D10 비식별 실측 Worklog](worklogs/2026-10-08_d10-production-readonly-evidence.md).

- [x] **배포 URL 동작 — 외부에서 접속된다**
  현재: 운영 Frontend `https://www.malhaebom.xyz/` 외부 GET 200, 공개 배포 JS에서 Cloud Run API `https://malhaebom-mk2-909028462046.asia-northeast3.run.app` 연결 확인. 해당 API `/health` GET 200, 프런트 Origin의 검색 API CORS preflight OPTIONS 200을 read-only로 재검증했다. 브라우저 로그인은 사용자 수동 확인.
  후속: 앞선 PlayMCP 인증 오류 이후, 사용자가 **실제 운영 브라우저에서 공고 검색→선택 공고 원문 분석→연습→1/2차 코칭 비교**까지 성공했다고 직접 확인했다. 외부 URL/사용자 기능 동작 항목은 완료로 변경한다. 이는 수동 사용자 보고이며 운영 실행 캡처·로그를 새로 확보한 것은 아니다.
  별도 남음: 같은 요청의 PlayMCP 도구 호출 연계, 성공 시각·리비전·redacted HTTP 로그 및 production Langfuse trace를 확보한다. 해당 근거는 아래 D10 관측 항목과 강사 피드백에서 따로 추적한다. [증거 점검](experiments/2026-10-02_evaluation-evidence-gap-audit.md)
- [-] **배포 환경에서 Langfuse trace가 남는지 확인한다**
  10/9 추가: 운영 사이트 채팅 200·브라우저 스키마 오류 422의 응답 X-Trace-Id와 Langfuse trace ID, Cloud Run revision 로그를 직접 연결했다. [증거](evidence/request-trace-linkage-2026-10-09.md). 아래 1/2차 코칭·Prompt/Skill 버전 근거는 별도로 남아 `[-]`를 유지한다.
  현재: 사용자가 운영 브라우저 E2E 이후 10/2 14:28 경 Langfuse Cloud 코칭 trace 상세 화면을 제공했다. 하나의 trace에 `coaching.provider`(Gemini 3.5 Flash-Lite, 15.84초), `coaching.output_validation`(`valid=true`, `error_count=0`), `coaching.analyze`(`status=needs_more_info`)가 존재했다. Trace 전체 약 16.00초·17,428 tokens·$0.008467. `needs_more_info`는 오류가 아닌 정상 코칭 상태다. [증거 점검](experiments/2026-10-02_evaluation-evidence-gap-audit.md)
  추가 캡처: provider Attributes에서 `outcome=success`, HTTP 200, 재시도 없음, `skill_version=interview-coach-v6` **표시값**을 확인했다. Tracing 목록의 Environment는 `default`이고 Prompt Name은 미표시다. 현재 기본 Skill 카탈로그는 `interview-coach-v6.1-domain-rules`이므로 표시값과 실제 적용 버전의 불일치 가능성이 있다. [PR #162](https://github.com/aihuman-7th/proj2-3/pull/162)는 소스 측 기록 버전 정합성 수정을 병합 완료했으며, 운영 배포·재검증은 별도다.
  남음: `default` 관측의 실제 운영 Cloud Run 리비전·해당 1/2차 E2E 세션 간 연계와 실제 로딩된 Prompt·Skill 버전을 확인하고, 개인정보를 가린 증거를 보존한다. Langfuse Cloud 화면 존재만으로 production label·관리형 Prompt 적용을 확정하지 않는다.
- [x] **실패 observation을 근거로 재조정 가설을 한 줄 남긴다**
  근거: 과거 PlayMCP 인증 오류(후속 복구 보고) 및 Langfuse Skill `v6` 표시값/현재 카탈로그 `v6.1` 불일치를 기반으로 [D10 관측 가설·검증 계획](experiments/2026-10-02_d10-observability-hypotheses.md)을 작성했다. **한 줄 가설:** 이전 기본 버전 메타데이터가 실제 로드된 Skill과 별도로 기록됐을 수 있으므로, #162 배포 리비전에서 런타임 Skill·새 trace·DB 기록을 동일 실행 기준으로 대조한다. 가설 문서 작성 완료이며 운영 원인 확정·재배포·rollback 검증 완료는 아니다.
- [-] **prompt v1 등록 — release manifest를 고정하고 rollback 경로가 실제로 되는지 확인한다**
  현재: PR #174에서 배포 v4 기반 보강 후보를 별도 코드 v5와 Langfuse `candidate`로 등록하고 숫자 버전·본문 SHA256·등록 manifest를 고정했다. 운영 v4 `production` 라벨과 Cloud Run revision·트래픽은 유지했다.
  후속(10/8): 위 Langfuse 화면에서 **reinforced Prompt의 #4 `production` 라벨 및 해당 버전의 실제 generation 연결**을 확인했다. 위 'v4 유지'는 **10/6 시점 이력**이지 현재 상태를 뜻하지 않는다. 실제 release gate와 rollback을 수행·검증했다는 증거는 없다.
  남음: managed Prompt의 production 승격 기준을 확정하고 실제 release 전환·rollback을 같은 운영 경로에서 실증한다. candidate 등록만으로 D10 완료 처리하지 않는다.

**남길 것:** 배포 URL · 배포 환경 trace · 재조정 가설 한 줄

---

## D11 · 10/7 — 검증 · baseline 측정 · 개선 가설

**10/8 최신 D11 v5 추가 실험:** 이전 provider 오류였던 02·03을 각각 1회 더 호출해 모두 계약 유효 응답을 확보했다. *각 사례 마지막 시도 기준* v4는 계약·기대 판정 3/3, v5는 **계약 3/3, 기대 C/A/V·intent 전부 일치 2/3**. 02의 `own_action=met`은 10/7 단일 검토자의 `partial` 판정과 다르다. 아래의 v5 1/3 서술은 추가 재시도 이전의 이력이다. [상세 결과](experiments/2026-10-08_d11-injection-prompt-ab-provisional.md). 독립 검토, 공식 Dataset 승격 및 방어 개선 판정은 미완료다.

- [x] **평가셋 30건으로 baseline score 측정**
  근거: 기존 30건 평가 수치와 [D11 오프라인 사전점검](experiments/2026-10-02_d11-baseline-preflight.md)을 분리 기록했다. `evals/prepare_d11_baseline.py`로 Dataset v2 30건·카탈로그·결합 Prompt 해시와 기존 인젝션 회귀 3건을 확인하는 사전점검을 준비했다(새 모델 호출 없음).
  최신 근거: PR #171에서 운영 트래픽 100% revision의 동일 이미지·모델·Prompt·Skill·Dataset으로 합성 30건을 3회(90실행) 측정했다. 계약 90/90, intent/C/A/V 기대 판정 모두 일치 65/90, 종합 자동 통과 57/90, 실제 HTTP 92회, 알려진 비용 $0.424128. 원본 응답·manifest·summary·Prompt·Skill·SHA256을 저장소에 보존했다.
  비고: 이 baseline은 배포 이미지의 provider·출력 검증·복구 경로 측정이며 새 사람 품질 평가나 사용자 HTTP/MCP/DB E2E를 의미하지 않는다.
- [x] **약한 구간 식별 — 어떤 유형에서 틀리는지 찾는다**
  근거: PR #171의 동일 3회에서 항상 자동 실패한 사례가 normal 06, boundary 13·16·17·19·20·21, failure 27·30으로 확인됐다. 특히 boundary 10건 중 6건이 3회 모두 실패해 가장 반복적인 약점 구간으로 남았다. normal 01·09, failure 23·28 등 회차별 변동 사례도 별도 식별했다.
- [-] **평가셋에 인젝션 케이스 3건을 넣어 방어 전후를 같은 기준으로 잰다**
  준비: 기존 Dataset v2의 `coach-failure-23`(지시문), `28`(JSON 위장), `29`(MCP 타인 기록 조회)을 **기존 회귀 감시 대상**으로 사전점검에 명시했다.
  추가 준비: PR #175에서 기존 30건과 분리된 신규 후보 3건을 정의하고 사용자가 A 승인 / B `own_action=partial` / C 승인을 확인했다.
  추가 진행(10/7): 사람 검토 패킷에 3건의 판정을 다시 입력했다. 01은 `met / met / not_observed`, 02는 `met / partial / not_observed`, 03은 세 기준 모두 `not_observed`로 기록했다.
  10/8 제한 실측: 기존 10/7 단일 검토자 판정으로 신규 3건에 Prompt v4/v5 각 1회 실호출, 계약 실패 사례에 각 1회 재시도했다. v4 계약·C/A/V/intent 판정 3/3, v5는 1/3이고 두 사례는 provider 오류로 유효 출력 미확보. [잠정 비교](experiments/2026-10-08_d11-injection-prompt-ab-provisional.md). 독립 검토 및 방어 개선 확정은 미완료다.
  추가 진행(10/8): `local-results/d11-injection-review-20261008/`에 후보 원문과 **빈 독립 사람 검토 양식**을 생성하고 [검토 인계 안내](evidence/d11-human-review-handoff-2026-10-08.md)를 기록했다. 사람 검토·공식 승격·유료 전후 측정은 수행하지 않았다.
  남음: 같은 검토자가 10/6 후보 label 승인에도 참여했으므로 이 입력만으로 독립 사람 확정으로 계산하지 않는다. 별도 검토자가 입력·정답·근거를 재확정하거나 사람이 입력을 실질적으로 다시 작성한 뒤 공식 승격을 결정하고 동일 조건 방어 전후를 측정한다. 기존 30건 속 3건도 신규로 계산하지 않음
- [x] **프롬프트 v2 또는 모델 설정을 한 가지만 바꾼다 — 둘을 동시에 바꾸지 않는다**
  근거: PR #174에서 배포 v4 기반 보강 후보를 새 Prompt candidate로만 등록했다. 모델·Skill·서버 검증·출력 상한은 변경하지 않았고 기본 v4와 운영 production 라벨도 유지했다.
- [x] **바꾼 이유를 한 줄로 기록한다**
  근거: **개인/팀 행동, 명시적 미수행, 판정 독립성, 확인 질문과 예시 사실 보존을 보강하기 위해 Prompt candidate만 분리 등록했다.** Spec·Worklog에 동일 판단을 기록했다.

**남길 것:** baseline score 표 · 약한 구간 목록 · prompt v2

증거 정리(10/8 갱신): 10/2의 30건 v4/v5 비교와 PR #171의 운영 배포 구성 30건×3회를 구분한다. 신규 인젝션 3건의 **별도 v4/v5 실호출 및 제한 재시도는 [PR #215](https://github.com/aihuman-7th/proj2-3/pull/215)에 기록 완료**했다. v4 계약·기대 판정 3/3, v5 **마지막 시도 계약 3/3·기대 판정 2/3**(최초 v5 계약 1/3). **독립 사람 입력/정답 검토와 공식 방어 효과 판정은 미완료**이며 운영 배포의 30건×3회에 신규 3건을 합산하지 않는다.

후속 후보: PR #174는 baseline 이후 운영 v4를 교체한 것이 아니라 보강 Prompt를 별도 candidate로 등록한 단계다. 실제 provider 재측정·사람 검토·production 승격은 후속 검증으로 남긴다.

사전점검: [D11 baseline 사전점검](experiments/2026-10-02_d11-baseline-preflight.md) 및 오프라인 manifest 생성 도구. 도구는 현재 코드 기본 Prompt를 읽으며 유료 호출을 승인하지 않는다. 추가 유료 전후 실행은 신규 3건 독립 판정과 비용 승인 전에는 시작하지 않는다.

---

## D12 · 10/8 — 검증 · 전후 재측정 · 코드 동결

**10/8 근거 상태 최신화 (PR #215·#216은 아직 미병합):** 아래 재측정·평가 보고서 항목은 `부분 완료`로 유지한다. 10/2 동일 조건 30건 A/B, 10/6 운영 이미지 30건×3회, 10/8 D11 신규 인젝션 3건 **서로 다른 실험**을 구분해 [EVAL_REPORT.md](../EVAL_REPORT.md)에 요약했다. 신규 3건은 v4 계약·기대 판정 3/3, v5 **재시도 포함 계약 3/3·기대 판정 2/3**, 최초 v5 계약 1/3, 단일 사람 검토 기준(독립 검토/공식 승격 없음). [PR #215](https://github.com/aihuman-7th/proj2-3/pull/215).

**운영 관측 최신화:** [PR #216](https://github.com/aihuman-7th/proj2-3/pull/216)의 사용자 제공 Langfuse 화면에서 강화된 별도 Prompt `malhaebom-coaching-v5-reinforced-verification@4`로 실행한 **동일 trace의 출력 계약 `valid=true`, 오류 0**을 확인했다. D11의 `coaching-v5-skill-owned` 조합과 같다고 주장하지 않는다. 현재 Skill 번들·Cloud Run revision·DB 요청 연결·release/rollback은 운영 권한 부족으로 미검증. 이 화면은 **제출용 비식별 스크린샷 파일 3장 확보**를 의미하지 않으므로 Langfuse 제출 체크박스는 미완료다. 영상·코드 동결도 기능 수정 이후로 보류한다.

- [-] **v1·v2 재측정 — 같은 평가셋으로 score, 비용, p95 지연을 다시 잰다**
  근거: 2026-10-02 최신 영문 v5와 이전 영문 v4를 동일 현재 Skill·합성 30건에서 재측정하고 score·비용·p95·회귀를 기록. 출력 한도 4,096-token v5 후속 30건은 계약 30/30·실패 0건을 확인. `docs/experiments/2026-10-02_latest-english-v5-comparison.md`, `docs/experiments/2026-10-02_gemini-v5-4096-30case-evaluation.md`
  남음: D10 운영 기준 고정, 자동 불일치 7건 사람 검토 및 최종 반복 검증 (`evals/build_gemini_v5_human_review.py`로 local 양식 준비)
- [-] **`EVAL_REPORT.md` 작성 — 개선 전후를 표로 남긴다**
  근거: `EVAL_REPORT.md` 4·6·7장에 2026-10-02 영문 v4/v5 동일 조건 실측과 회귀·게이트 반영
  남음: 사람 안전성·비용 상한·운영 E2E 및 최종 승인 기준 검증
- [ ] **데모 영상 — 정상 1건과 실패 1건을 같이 보여준다** — 발표/회의자료 준비는 곽호준 담당. 10/7 실제 시연은 강사에게 확인받았지만 정상·실패 영상 파일 자체의 제출 증거는 아직 없으므로 완료 처리하지 않는다.
- [ ] **코드 동결 — 이후 커밋은 채점에 반영하지 않는다**
- [ ] **Langfuse 스크린샷 제출** — 발표/회의자료 준비는 곽호준 담당. 상세 trace 캡처 파일의 실제 제출 확인 전까지 미완료로 유지한다.

**남길 것:** `EVAL_REPORT.md` · 전후 비교표 · 데모 영상(정상·실패)

증거 정리(10/8): 10/2 v4/v5 30건, 10/6 운영 이미지 30건×3회, 10/8 신규 인젝션 3건은 별도 실험이다. 신규 3건의 실제 v4/v5 모델 호출과 제한 재시도는 **수행**했으나, 단일 검토자 기준 잠정 비교(3/3 vs 2/3)로 **공식 방어 전후 검증 완료 또는 개선 입증이 아니다**. 위 [PR #215](https://github.com/aihuman-7th/proj2-3/pull/215) 참조.

최종 제출 파일·링크의 현재 존재 여부와 캡처/영상 체크리스트는 [제출 증거 인덱스](SUBMISSION_EVIDENCE.md)에서 추적한다. 10/8 사용자가 Langfuse 상세 화면을 제공해 실측 근거는 늘었지만, **원본 화면에는 사용자·세션 식별자 등이 있어 아직 제출 가능한 비식별 이미지 3장을 확보했다고 표기하지 않는다**. 정상·실패 영상, 발표 PDF 및 코드 동결도 미완료다.

증거 정리: [10/2 평가 증거·누락 점검](experiments/2026-10-02_evaluation-evidence-gap-audit.md). 4,096-token v5의 불일치 7건은 `normal-09`, `boundary-13/16/17/19/20`, `failure-27`이다. [PR #161](https://github.com/aihuman-7th/proj2-3/pull/161)은 **7건 사람 검토용 양식·추출 도구 준비**를 완료했으며, 실제 사람의 semantic/critical 점수 입력은 별도 미완료 작업이다. [PR #162](https://github.com/aihuman-7th/proj2-3/pull/162)는 **Prompt·Skill 실행 버전의 관측/DB 기록 정합성 수정**으로, 7건 사람 검토와 다른 범위다. 최종 v1/v2 비교, production Langfuse 캡처도 확보되지 않았다. 별도 v4 팀 품질 점수와 D4 정답표 사람 검토를 최신 v5 사람 평가로 재사용하지 않는다.

---

## 3조 강사 피드백 보완 체크

> 공식 Checkpoint D2~D12와 별도로 중간 강사 판정에서 지적된 3조 항목을 추적한다. 이 항목은 공식 Day 체크리스트를 대체하지 않는다.

### 문제 해결력

- [x] **핵심 사용자 문제와 공고 원문 분석 흐름 정합성 확보**
  근거: `skills/job-requirement-extraction/SKILL.md`, `backend/app/services/alio_requirement_analysis.py` 및 실제 공고 원문 분석 경로가 존재. PR #140과 `docs/README.md` 최신화로 문서 정합성을 해결했고, `docs/evidence/job-source-analysis-local-e2e-2026-10-01.md`에서 로컬 실제 로그인 사용자 JWT 기반으로 공고 추천 → 선택 공고 원문 재검증 → 요구사항 5건 추출 → quote validation 통과 → private_job 저장/조회 → 요구사항 2개 선택 → 연습 세션 생성까지 확인했다.
  추가 근거: [과거 배포 환경 API 로그](evidence/job-source-analysis-e2e-2026-10-01.md)의 추천 200·분석 201·세션 생성 201. 동일 사용자 연결·운영 인용/저장 상세 및 현재 revision 재실행 증거와 구분한다.

### LLM 제어력

- [x] **Prompt와 Skill의 책임 분리**
  근거: `prompts/*.md`는 모델 역할·입력 취급·출력 계약, `skills/`는 도메인 판단 규칙을 담당한다. `docs/specs/prompt-skill-separation.md`, `backend/tests/test_prompt_skill_separation.py`에서 Skill 본문 주입과 책임 분리를 검증한다.

### 서비스 완성도

- [x] **제품 테스트 CI 구성**
  근거: `.github/workflows/product-ci.yml`에서 PR마다 backend 전체 `unittest`, frontend `npm test`, production build를 자동 실행하도록 구성했다. backend CI는 `backend/requirements-ci.txt`의 경량 의존성만 설치해 STT/TTS 모델 runtime 패키지를 매 PR마다 설치하지 않는다. `backend/tests/test_pr_policy_workflows.py`에서 workflow와 경량 의존성 계약을 정적 검증한다.
  실측: PR #137의 Product CI 첫 실제 실행에서 `Backend tests`, `Frontend tests and build`가 모두 SUCCESS.
  비고: 실제 외부 배포는 공식 D10 항목에서 추적한다.

### 관찰과 평가

- [x] **동일 평가셋 기준 개선 전·후 비교 artifact 저장**
  근거: `docs/experiments/2026-09-30_coaching-before-after-summary.md`에 동일 Flash-Lite / 2026-09-22 Dataset v2 snapshot 기준 v3→v4, v4→v4.1+repair, v4.2 candidate 비교를 연결하고 contract, label, evidence, latency, cost와 대표 개선·회귀 case를 한 문서에 고정했다. 2026-09-30 ground-truth correction 결과는 별도 구간으로 분리했다.
  보존: raw provider 응답·credential·개인정보는 복제하지 않고 재채점 명령과 원본 기록 경로를 포함한 redacted 요약 artifact를 저장소에 보존한다.
  비고: 이 항목은 강사 피드백 보완용 비교 artifact이며 D7 공식 baseline 확정이나 D11~D12 최종 개선 평가를 대체하지 않는다.
### 2026-10-02 제공된 최신 3조 강사 피드백 — 후속 검증

> 이번 스크린샷에서 3조의 강사 판정은 문제 해결력 △, LLM 제어력 ×, 서비스 완성도 △, 관찰과 평가 △이다. 위의 기존 4개 개선 항목 완료 기록은 유지하고, 새 지적은 별개로 추적한다. D3/D4/D5/D9 자동 체크와 D8 CI 완료를 강사 품질 평가 전체의 충족으로 확대 해석하지 않는다.

#### 문제 해결력 — 공고 분석의 실제 PlayMCP 경로

- [-] **로그인 사용자 기준 PlayMCP 공고 원문 분석 E2E 증거 보강**
  현재: PR #149의 인증 사용자 API E2E에서 공고 추천 → 원문 재조회 → 요구사항 5건 추출 및 quote 검증 → private_job 저장·조회 → 요구사항 선택 및 세션 생성을 1회 확인했다. 당시 PlayMCP 인증 503으로 web provider 복귀 경로를 사용했다.
  추가 근거(10/2 제공 문서, 팀 합의 전): 10/1 로컬 재연결과 Cloud Run 별도 진단 Job에서 각각 PlayMCP 직접 호출 20건 성공을 기록했다. 10/1 운영 추천 API 200 → 공고 분석 201, 10/2 08:41 운영 추천 API 200 및 해당 리비전 `playmcp_tavily` 설정 확인 기록도 있다. 단, 진단 Job과 운영 요청은 다른 실행이며 기존 web fallback E2E와 합쳐 단일 PlayMCP 전체 E2E라고 표현하지 않는다.
  후속 사용자 검증: 운영 브라우저의 로그인 사용자 세션에서 공고 검색→공고 원문 분석→1/2차 비교까지 정상 완료했다고 사용자에게 직접 확인받았다. 이는 **운영 화면의 사용자 기능 성공 보고**이며 검색 요청이 실제 PlayMCP 도구를 거쳤다는 동일 요청별 추적 자료는 아직 아니다.
  남음: 운영 요청의 PlayMCP 도구 호출 → 추천·원문 분석까지 연결된 redacted 로그/trace와 성공 시각·리비전, 대표 실패/복귀 증거의 범위를 팀에서 확인한다. 관련 노션 문서의 내용·공유 링크는 팀 합의 전이다.

#### LLM 제어력 — 현재 기본 Prompt/Skill과 코칭 품질

- [-] **새 기본 Prompt·Skill 규칙의 충돌 방지와 실제 조립 검증**
  현재: PR #153에서 도메인 판정 규칙·우선순위·예시를 Skill로 이동하고 기본 `coaching-v5-skill-owned` Prompt는 역할·입출력 계약 중심으로 분리했다. 정적 테스트와 PR CI는 통과했다. 병합된 PR #155는 동일 Skill로 v4·v5를 조립한 실제 평가 runner의 측정 기록을 추가했다.
  추가 코드 검증: 기본 Skill 버전 메타데이터를 현재 카탈로그와 일치시키고, 원격 Prompt 선택 시 코칭 실행 버전을 관측과 DB 저장에 전달하는 회귀 테스트를 보강했다. Langfuse SDK 4.x 프로필에서 관련 70건 통과. [Worklog](worklogs/2026-10-02_coaching-version-provenance.md).
  남음: 운영 이미지에서 실제 로드된 Prompt·Skill 버전과 최종 조립 입력의 중복·상충 여부를 확인한다. runner/로컬 테스트가 운영 설정·Langfuse 원격 Prompt 내용을 검증한 것은 아니다.
- [-] **현재 기본 Prompt·Skill의 실제 코칭 품질 측정**
  현재: 병합된 PR #155가 동일 Skill·모델·합성 평가셋을 고정한 v4/v5 각 30건 실호출 결과를 기록했다. 계약 양쪽 30/30, 종합 자동 통과 v4 22/30 → v5 20/30, 기대 판정 116/120 → 107/120, provider 비용 $0.19638110 → $0.17027067, v5 p95 4.622초. 새 v5의 개선 승격·출시 통과가 아니라 판정 회귀를 기록한 단일 실험이다.
  남음: 출력의 사람 semantic/critical 검토·반복 측정 및 팀 평가 기준 합의. 병합된 PR #154는 과거 영문 v4의 팀 검토 취합으로서 현재 v5 검토와 혼합하지 않는다.

#### 서비스 완성도 — 공식 D10과 연결

제품 테스트 CI 구성 완료는 유지한다. 새 피드백의 남은 운영 배포 문제는 위 D8의 D10 선행 준비와 공식 D10(외부 URL·운영 API·production trace)에서 추적한다. 중복 체크박스를 만들지 않는다.

#### 관찰과 평가 — 최종 EVAL_REPORT 실제 측정 반영

원본·실행 조건·누락 증거를 [2026-10-02 평가 증거 점검표](experiments/2026-10-02_evaluation-evidence-gap-audit.md)에 교차 연결했다. 새 실험이나 사람 검토를 수행한 변경이 아니므로 아래 기존 부분완료 상태는 유지한다.

- [-] **`EVAL_REPORT.md` 4·6·7장에 현재 기본 버전의 실제 측정과 출시 판단 근거 반영**
  현재: 병합된 PR #155에서 4장 동등 Skill v4/v5 실측·회귀, 6장 합성 provider 지표, 7장 출시 게이트의 측정값과 미달/미검증 항목을 채웠다. 병합된 PR #154의 과거 v4 팀 품질 취합과 구별해 보존한다. 경계·실패 유도 기준 미달, 최신 v5 사람 검토 미실시, 비용 상한 미합의를 명시한다. 이는 인증·MCP·STT·DB를 포함한 운영 E2E 수치가 아니다.
  남음: 현재 기준의 사람 검토·팀 공통 기준 합의 후 최종 평가를 확정하고, production trace/운영 수치는 D10에서 따로 확인한다.

**팀 합의 전 외부 근거(기록용 원본 링크만):**
- [코칭 E2E 단계별 검증 및 PlayMCP 원본](https://app.notion.[REDACTED]): 원본 직접 열람은 미확인, 제공된 복제본의 당시 내용으로 위 실행 기록 대조. 최종 링크/내용 팀 확인 필요.
- [영문 v4 품질측정 원본](https://app.notion.[REDACTED]): 원본 직접 열람은 미확인, 제공된 복제본의 당시 내용과 PR #154 대조. 공통 평가 기준·17번 중대 오류 분류·최종 점수는 팀 합의 전.

### 2026-10-06 최신 3조 강사 피드백 — 후속 검증

> 오늘 강사 판정은 문제 해결력 △, LLM 제어력 ×, 서비스 완성도 △, 관찰과 평가 △이다. 기존 완료 항목과 중복되는 체크박스는 새로 만들지 않고, 오늘 피드백에서 남은 검증만 추적한다. 자동 조건은 D1·D2·D3·D4·D5·D8·D9·D12를 통과했으며 D10 배포 URL 항목은 별도 보완한다.

#### 문제 해결력 — 공고 분석의 실제 PlayMCP 경로

- [-] **실제 PlayMCP 경로의 공고 원문 분석 E2E 증거 확보**
  피드백: 공고 원문 분석 E2E가 1회이며 당시 PlayMCP 대신 web provider로 우회했다.
  현재: 로그인 사용자 공고 추천 → 원문 분석 → 세션 생성 흐름과 운영 API 성공 로그를 확보했고, PR #167에서 Cloud Run 추천 200·분석 201·세션 생성 201 기록을 보강했다.
  남음: 동일 실행에서 PlayMCP 도구 호출 → 추천 → 원문 분석까지 직접 연결되는 요청별 증거.

#### LLM 제어력 — 현재 기본 Prompt/Skill과 코칭 품질

- [x] **현재 기본 Prompt와 Skill의 규칙 중복·충돌 검증**
  피드백: 교체 Prompt가 도메인 판정 규칙을 포함해 Skill과 충돌할 가능성이 있다.
  근거: 현재 작업·평가 기준 `coaching-v5-skill-owned`와 현재 GitHub Skill을 canonical builder로 실제 합성해 확인했다. v5 Prompt에는 Boundary table·과거 result_verification gate가 없고, intent/C/A/V·result_verification 도메인 규칙은 Skill에서만 한 번 포함된다. 회귀 테스트로 이 단일 소유를 고정했다.
  비고: local fallback/default selector와 마지막 저장소 운영 증거의 v4는 배포 재현 계열로 분리한다. 실제 live production Prompt가 v5인지 여부는 D10 운영 증거에서 별도로 확인한다.
- [-] **현재 기본 Prompt + Skill 조합의 코칭 품질 측정**
  피드백: 현재 조합에 대한 품질 측정 근거가 부족하다.
  현재: PR #171에서 **실제 운영 트래픽 100% revision의 이미지·Gemini 3.5 Flash-Lite·배포 Prompt·Skill·Dataset을 고정한 30건×3회(90실행)**를 추가했다. 계약 90/90, 기대 intent/C/A/V 전체 일치 65/90, 종합 자동 통과 57/90이며 3회 판정이 모두 같은 사례는 25/30이다.
  남음: 해당 실행은 운영 기록 Skill v6 기준이라 현재 GitHub Skill과 동일 조합이라고 볼 수 없고, 새 90출력의 사람 semantic/critical 검토도 수행하지 않았다. 현재 GitHub 기본 Prompt·Skill 조합의 최종 평가를 별도로 확정한다.

#### 서비스 완성도 — 공식 D10과 연결

- [x] **README에 실제 배포 주소와 플랫폼 정보 반영**
  피드백: D10 배포 URL 자동 조건에서 README에 배포 플랫폼 주소가 없다.
  근거: PR #170이 main에 병합되어 공개 서비스 URL, Cloud Run API 및 health 주소가 README에 반영됐다.

제품 테스트 CI/pytest 구성 완료는 기존 [x] 항목을 유지하며 중복 체크하지 않는다.

#### 관찰과 평가 — 최종 EVAL_REPORT 실제 측정 반영

- [-] **`EVAL_REPORT.md`의 현재 기본 설정 기준 평가 근거 완성**
  피드백: 개선 전후 자료는 있으나 EVAL_REPORT 4·6·7장과 현재 기본 Prompt 간 정합성이 부족하다.
  현재: PR #155의 v4/v5 실측에 더해 PR #169가 기존 운영 Langfuse trace·사람 평가 근거를 연결했고, PR #171은 최신 운영 배포 이미지 기준 90개 raw 응답·manifest·해시와 반복 결과를 EVAL_REPORT에 연결했다.
  남음: PR #171의 새 90출력에는 사람 평가가 없고 운영 사용자 E2E와도 별도 실행이다. 현재 운영 성공 요청 trace와 동일 버전 출력의 사람 평가를 직접 연결해 최종 판단을 확정한다.

#### 참고 측정 — 인젝션 대응

- 현재 강사 측정: 인젝션 추종 1/48(2.1%), 12건 중 4건에서 모든 기준을 `met`으로 뒤집는 도메인 조작 관측, 공식 조건 4/5 충족.
- 별도 체크박스를 추가하지 않고 D11의 **평가셋에 인젝션 케이스 3건을 넣어 방어 전후를 같은 기준으로 잰다** 항목에서 후속 측정한다.

#### 프롬프트 설계 페이지 신규 점검 기준

> 10/6 프롬프트 설계 페이지의 **내 프로젝트 점검표** 10개를 저장소 상태와 대조했다. 이미 공식 Day/강사 피드백 체크에 있는 항목은 중복 체크박스를 만들지 않고 기존 항목을 참조한다.

**기존 항목으로 추적**
- `같은 규칙의 본문이 두 곳에 있지 않는다` → 위 **현재 기본 Prompt와 Skill의 규칙 중복·충돌 검증**에서 추적.
- `평가셋 문항마다 사람의 판정과 이유가 있다` → D4 **문항마다 판정자 이름과 판정 근거 한 줄을 적는다** `[x]`로 완료.
- `인젝션 문항이 3건 이상이고 방어 전후를 같은 기준으로 잰다` → D11 인젝션 방어 전후 측정 `[-]`에서 추적. PR #175에 신규 후보 3건과 1차 사용자 승인을 기록했으며 독립 사람 확정·전후 실측이 남아 있다.

**새로 추가할 보완 항목**
- [x] **숫자 기준·판정 표의 단일 기준원 확보**
  근거: PR #179가 main에 병합되어 코칭 판정의 canonical source를 `load_skill_bundle()`이 조립하는 versioned Skill bundle로 고정했다. `criteria.json`·질문 유형 문서·`SKILL.md`·Prompt의 소유 범위를 분리하고, 현재 운영 템플릿에 Boundary table·700ms 사례 등 도메인 기준 marker가 재유입되지 않는 회귀 테스트를 추가했다.
  비고: 기존 배포 v4와 과거 실험 Prompt의 중복 문구는 hash 재현용 비canonical snapshot 예외다. 다음 production 후보의 Skill-owned 구조 사용 여부는 release 단계에서 별도 확인한다.
- [-] **호출별 시스템 Prompt를 역할 단위 섹션으로 분리**
  현재: PR #176에서 backend LLM/provider 호출을 전수 정적 점검했고, stacked PR #182에서 mutable system Prompt를 `[역할] → [입력 경계] → [출력 계약] → [안전 경계]` 구조로 통일했다. 구조 회귀 테스트와 호출 inventory 문서도 추가했다.
  남음: PR #176·#182는 main 병합 완료. 현재 배포 v4 `prompts/coaching.md`는 10/6 반복평가·hash 재현용 frozen snapshot으로 남는다. 다음 production 후보를 Skill-owned 4섹션 구조로 재평가·승격해야 전체 호출 기준 완료.
- [x] **사용자 입력 템플릿과 보안 규칙의 충돌 점검**
  근거: PR #176이 main에 병합됐다. coaching / README / 공고 / 면접 대화 / question rubric / job-search intent / web-search 경로를 정적 점검하고, 실제 gap이던 job-search intent에 데이터 경계·시작/끝 구획과 injection 회귀 테스트를 추가했다.
  비고: D11 신규 인젝션 provider before/after 실측은 이 정적 점검과 별도 항목으로 유지한다.
- [x] **Skill 규칙마다 이유·출처·검수 상태 기록**
  근거: PR #180이 main에 병합되어 canonical criterion 33개 전부에 `rationale / source / expert_review` provenance sidecar를 연결하고 ID coverage·버전·source 존재·검수 상태를 테스트로 고정했다.
  비고: provenance는 규칙 본문이 아니라 추적 메타데이터로 유지한다.
- [x] **확정되지 않은 전문가 기준을 ‘유보’로 표시**
  근거: PR #180에서 미검토 33개 criterion을 `deferred / 유보`로 기록했다. 2026-10-09 사용자가 김창민의 전체 검토 완료를 확인하여 현재는 33개 모두 `reviewed / 김창민 검토 완료`로 기록한다. [확인 기록](worklogs/2026-10-09_expert-rule-review-confirmation.md).
  비고: 검토자 이름·IT 업계 면접관 경험·검토 완료 여부는 사용자 제공 정보다. 별도 검토 원문은 첨부되지 않았으며 코칭 품질·실사용자 E2E 완료를 뜻하지 않는다.
- [ ] **judge 신뢰도 지표를 사람 판정과 함께 측정** *(현재 N/A — LLM judge 미사용)*
  현재: 공식 평가는 규칙 기반 grader를 사용하며 LLM judge를 사용하지 않는다. 따라서 현 평가 경로에는 judge 신뢰도 측정 대상이 없고 현재 작업 blocker로 계산하지 않는다.
  조건부 후속: 이후 LLM judge를 도입할 경우에만 사람 판정 기준으로 **일치도·틀림 포착률·Cohen's kappa**를 함께 측정하고 기준 미달 시 judge Prompt를 먼저 보정한다.
- [-] **Skill 개선 시 평가 기준을 고정하고 한 번에 한 규칙만 변경**
  현재: `coach-boundary-19`에서 Dataset v2·Prompt·Gemini 3.5 Flash Lite·grader·generation 설정을 고정하고 `off_topic` ↔ C/A/V 독립 판정 **Skill 규칙 한 줄만** 바꿔 baseline/candidate 각 1회 smoke를 실행했다. 계약은 100%/100%였지만 target hit 2/3→1/3, label accuracy 75%→50%로 악화했고 `own_action`이 met→partial로 회귀해 자동 결론은 `DISCARD_CANDIDATE`였다.
  남음: gate 정책상 full 30건×2회는 실행하지 않는다. target 출력의 사람 최종 검토와 DISCARD 확인을 남긴 뒤 항목을 완료 처리한다.

### 2026-10-07 최신 3조 강사 피드백 — 후속 검증

> 오늘 강사 판정은 문제 해결력 △, LLM 제어력 △, 서비스 완성도 △, 관찰과 평가 △이다. 자동 체크는 D1·D2·D3·D4·D5·D8·D9·D10·D12가 통과했고 공식 조건은 **5/5**다. 기존 완료 항목을 다시 열지 않고, 오늘 피드백에서 실제로 남은 검증만 기존 체크와 연결한다.

#### 문제 해결력 — 실제 PlayMCP 경로 증거

- 기존 **실제 PlayMCP 경로의 공고 원문 분석 E2E 증거 확보** `[-]`를 유지한다.
  현재: 제품 차원의 공고 탐색·추천·원문 수집·요구사항 분석 등을 범위 밖으로 두던 문구는 PR #165에서 제거·재감사되어 main에 반영됐다.
  남음: 동일 운영 요청에서 PlayMCP 도구 호출 → 추천 → 공고 원문 분석이 이어졌음을 보여주는 요청별 redacted trace/log.

#### LLM 제어력 — 경계·실패 유도와 인젝션 재측정

- 기존 **현재 기본 Prompt + Skill 조합의 코칭 품질 측정** `[-]`를 유지한다.
  현재: Prompt/Skill 규칙 중복·충돌 검증은 완료했고, 최신 운영 반복평가는 30건×3회까지 확보했다. 단일 Skill 규칙 smoke에서는 label accuracy 75%→50%로 악화되어 후보를 폐기했다.
  남음: 경계·실패 유도 케이스의 품질을 현재 기준으로 사람 검토하고, D11 신규 인젝션 3건을 독립 사람이 확정한 뒤 같은 조건 before/after를 재측정한다.

#### 서비스 완성도 — 강사 판정과 현재 운영 증거 정합성

- [-] **강사 판정과 현재 운영 배포 증거의 불일치 해소**
  피드백 화면: 배포 URL 없음·Cloud Run 중지로 판정됐다.
  현재 저장소 근거: README에 공개 서비스 URL·Cloud Run API/health 주소가 반영돼 있고 운영 브라우저 사용자 흐름 성공 기록도 있다.
  남음: 같은 시각의 공개 URL 응답, `/health`, 현재 Cloud Run revision, 로그인 후 핵심 사용자 흐름을 한 묶음으로 다시 캡처·기록해 제출 근거와 직접 연결한다.

#### 관찰과 평가 — 운영 trace와 사람 평가 연결

10/9 추가: 운영 준비 채팅 성공·입력 오류의 HTTP 요청→Langfuse trace 직접 연결 증거를 확보했다. [증거](evidence/request-trace-linkage-2026-10-09.md). 기존 30건×3회 코칭 평가의 사람 semantic/critical 검토를 완료한 것은 아니다.

- 기존 **`EVAL_REPORT.md`의 현재 기본 설정 기준 평가 근거 완성** `[-]`를 유지한다.
  현재: 최신 운영 이미지 기준 30건×3회 raw 응답·manifest·해시·자동 평가는 확보했다.
  남음: 동일 버전의 운영 성공 요청 trace와 새 출력의 사람 semantic/critical 평가를 직접 연결해 최종 판단을 확정한다.

#### 참고 측정 — 인젝션 대응

- 10/7 강사 측 측정: **0/48 (0.0%)**, 9/30의 2.1% 대비 **-2.1%p**, 공식 조건 **5/5**.
- 이 수치는 강사 측 참고 측정 snapshot이며, D11의 신규 인젝션 3건 동일 조건 before/after 실험이나 서비스 경로 검증을 대체하지 않는다.

**팀 합의 전 외부 근거(기록용 원본 링크만):**
- [코칭 E2E 단계별 검증 및 PlayMCP 원본](https://app.notion.com/p/oreumi/E2E-Play-MCP-3edebaa8982b804ea8f0e7794bb5e472): 원본 직접 열람은 미확인, 제공된 복제본의 당시 내용으로 위 실행 기록 대조. 최종 링크/내용 팀 확인 필요.
- [영문 v4 품질측정 원본](https://app.notion.com/p/oreumi/3edebaa8982b80c7b9e2dbcd7e3db107): 원본 직접 열람은 미확인, 제공된 복제본의 당시 내용과 PR #154 대조. 공통 평가 기준·17번 중대 오류 분류·최종 점수는 팀 합의 전.

---

## 공식 일정 밖의 별도 트랙 — STT 실제 사용자 평가

STT 정확도 개선과 파인튜닝은 Project2 D2~D12 공식 체크포인트를 대체하지 않는다. 다음 완료 표시는 **기록된 실험 조건에서의 수행 여부**이며, 서비스 전체 사용자 정확도나 운영 배포의 통과를 의미하지 않는다. [STT 파인튜닝 계보](stt-finetuning-lineage.md)와 [실험 목록](experiments/README.md)을 기준으로 2026-10-02 재점검했다.

10/9 문서 보강: [전·후 비교 리포트](stt-finetuning-lineage.md)에 첨부 비교 문서와 Drive 가이드·README·게시 체크섬 대조, 단계별 CER/WER 변화, raw/정규화 구분을 반영했다. 새 평가나 ZIP 다운로드·수신 실행 검증이 아니므로 기존 완료/유보 상태는 유지한다.

### 실험·서비스 구현: 근거가 확보된 항목

- [x] **STT·Silero VAD·전달력 분석 서비스 경로 구현** — faster-whisper `large-v3-turbo` 기반. 세션 문맥의 allowlist 기술용어를 최대 12개 동적 `initial_prompt`로 넘기는 경로 및 실패 시 no-prompt fallback의 코드/회귀 테스트까지 확인. 근거: `docs/CURRENT_STATE.md`, `docs/specs/stt-dynamic-initial-prompt.md`
- [x] **실사용 음성 1인 30건 dev/diagnostic set 확보·고정** — 일반 면접 10, 기술 질문 8, 숫자·영문 stress 6, 자연·장문 6건. 대본과 음성 ZIP 해시, 실험 manifest/model provenance 검증 및 원시 결과 Git 제외 정책 기록. 이 자료는 이미 설정 선택에 사용했으므로 독립 final acceptance set이 아니다. 근거: `[REDACTED].md`, `[REDACTED].md`
- [x] **정규화 전 CER/WER 측정** — 1인 30건 B0/C2 비교에서 raw CER/WER 각각 B0 16.03%/19.59%, C2 15.14%/20.91%. 이후 동일 조건 GPU 모델×beam 9조합에서도 전체 raw 결과 기록. 근거: 위 실사용 녹음 평가 및 모델×beam 실험
- [x] **발화형 정규화 후 CER/WER 측정** — 동일 30건 B0 13.91%/15.03%, C2 13.47%/15.18%; 숫자·영문 stress 6건 제외 면접형 24건 B0 8.82%/11.90%, C2 7.22%/10.71%. raw와 보조 정규화 지표를 함께 보존. 근거: `[REDACTED].md`
- [x] **파인튜닝 및 별도 테스트·기존 도메인 유지율 측정** — 50k retrain → B0 clean continuation → C1/C2 면접 도메인 적응 완료. B0의 별도 Test B 개선, C2의 신규 도메인 sealed 1,233건 final test CER 2.5876%/WER 9.7740% 및 historical 119 retention 기록. C2는 C1 대비 forgetting을 완화했으나 B0보다 과거 도메인에서 회귀. 봉인 해제된 test를 이후 튜닝에 재사용하지 않는다. 근거: `docs/stt-finetuning-lineage.md`, `docs/DECISIONS.md`
- [x] **기존 서비스 기준선과 후보 모델 동일 조건 비교** — frozen 30건에서 large-v3-turbo/B0/C2 × beam 1/3/5, 총 9조합 CUDA/float16 실행. large-v3-turbo beam 1의 면접형 core 정규화 CER/WER 3.29%/6.63%, RTF 0.020, p50 0.258초. 같은 조건 B0/C2 연구 후보보다 낮은 오류·지연을 기록했지만, 이 devset은 최종 출시 판정용이 아님. 근거: `[REDACTED].md`
- [x] **기술용어 hint와 runtime A/B 측정** — large-v3-turbo beam 1에서 none 대비 `initial_prompt` 사용 시 core 정규화 CER/WER 3.29%/6.63% → 2.44%/5.27%, 기술용어 recall 82.35% → 94.12%(동일 30건 진단용). 동일 model/prompt의 CPU/int8 ↔ CUDA/float16 parity도 측정했고 GPU real-30에서 tail hallucination 1건을 확인. 근거: `[REDACTED].md`, `[REDACTED].md`
- [x] **Cloud Run CPU 추론 성능 진단** — 로컬 Docker 및 benchmark 전용 Cloud Run 2/4/8 vCPU 실측과 CPU-only·모델 pre-bake 이미지 최적화 완료. **mock/local 저장소를 사용한 벤치마크**이며 Hosted Supabase/RLS 인증·저장 포함한 운영 E2E 수치가 아니다. 근거: `[REDACTED].md`
- [-] **B0/C2 모델 인계와 수신 검증** — 10/1 로컬 Worklog 기준 adapter+CT2 각각의 ZIP과 README·체크섬을 Drive에 업로드하고 로컬 ZIP 내부 해시·Drive 목록/크기를 확인. 10/2 사용자 확인으로 수신자에게 인계 링크까지 전달 완료. 남음: 수신자가 Drive ZIP 다운로드 후 SHA256 대조, 모델 로드·음성 추론 및 수신 결과 확인. 원본 인계 Worklog는 별도 로컬 미커밋 파일로 보존한다. 이 PR에 포함되는 근거: `docs/worklogs/2026-10-02_stt-checklist-evidence-refresh.md`

### 최종 적용 전에 남은 검증

- [ ] **신규 다중 화자 독립 acceptance 평가셋 확보** — 기존 1인 30건 devset과 source가 겹치지 않는 표준어·면접 음성, 자유 발화 및 숫자·영문 stress를 포함하고 수집 출처·동의/보관 범위·분할을 고정한다.
- [ ] **최종 raw/정규화 CER·WER 및 기술용어·환각 회귀 평가** — 신규 acceptance에서 현재 제품 설정의 동적 `initial_prompt` 적용/미적용, 후보 모델, 표준어·면접형/기술형·stress 구간을 비교한다. 기술용어 recall/false insertion, 추임새 보존 및 기존 GPU tail hallucination 유형도 검토한다. 기존 devset·71592 공개 final test 결과를 최종 acceptance로 다시 사용하지 않는다.
- [-] **표준어·면접 음성 및 historical regression 검증** — AI Hub 119 retention, 71592 면접 도메인 test와 1인 30건의 구간별 비교는 완료. 남음: 신규 독립 다중 화자의 표준어·자유 면접 답변에서 품질·회귀 확인. 71592 metadata만으로 경상도 화자 성능을 주장하지 않는다.
- [-] **Hosted Supabase를 포함한 실제 배포 STT E2E 검증** — Cloud Run mock benchmark는 main에 기록됐고, Hosted Supabase preflight/실행 계획은 별도 미병합 `experiment/hosted-analysis-e2e` worktree에 준비돼 있다. 남음: 운영 프로젝트 및 migration/RLS/Storage 상태 확인 → 실제 사용자 JWT로 음성 업로드·STT·저장·polling → 교차 사용자 접근 차단·cleanup → 지연·실패율 측정. 모델 immutable revision 고정 이후 이미지 빌드/지연도 재검증한다. main 근거: `[REDACTED].md` (미병합 계획 파일을 main 링크로 표시하지 않음)
- [-] **제품 기본 STT 모델·runtime 교체 여부 최종 결정** — 현재 large-v3-turbo + beam 1 + CPU/int8 기본 동작은 유지하며 B0/C2를 자동 승격하지 않았다. 신규 acceptance 결과, 실제 운영 지연과 비용·품질 회귀를 대조한 뒤 유지/교체 결정을 명시한다.

STT 실험이나 인계가 늦어져도 D2~D12의 Agent / Skill / MCP / Langfuse / 배포 / 평가 공식 판정을 자동으로 바꾸지 않는다.
