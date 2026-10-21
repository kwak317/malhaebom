# Requirements

이 문서는 **공식 Project2 요구사항과 말해봄 적용 해석을 구분하는 유일한 canonical 요구사항 문서**다. 팀이 좁힌 범위의 canonical은 [CONSTRAINTS](CONSTRAINTS.md), 평가 실행 계획은 [evals/README](../evals/README.md)다.

> **기존 코드 이관 반영, 공식 조건 실행 검증 전**. 아래 조건은 완료 사실이 아니다. 현재 상태는 [CURRENT_STATE](CURRENT_STATE.md)를 따른다. 코드·배포·측정·검수 증거 없이 PASS로 표시하지 않는다.

## 출처와 해석 범위

2026-09-16 제공된 루트 입력 `PROJECT2_REQUIREMENTS.md`를 기존 프로젝트 요구사항과 병합했다. 입력 문서가 명시한 원자료:

- [Checkpoint Project2 안내](https://checkpoint.habix.ai/aihuman-7th/project2)의 2026-09-14 저장본
- 2차 팀 프로젝트 가이드 v3 (2026-09-11)
- 2차 프로젝트 계획서 보완 제출 양식 (9/18 착수 세션 전 제출)
- [저장된 웹페이지 요약](https://github.com/nanocode00/factory-agent-hub/blob/main/requirements/project2-webpage.md)

입력 작성자는 PDF/DOCX를 대조했다고 설명하지만, 이번 작업은 제공 Markdown의 통합이며 해당 원자료를 새로 대조한 작업이 아니다. 입력에도 Checkpoint live 재조회 실패가 명시되어 있다. 따라서 아래 공식 조건은 **제공 자료 기준**이며 최신 공지 확인 여부와 구분한다. 충돌은 삭제하지 말고 Worklog/DECISIONS에 근거와 적용 결정을 남긴다.

## 공식 Project2 요구사항

### 프로젝트 정체성과 평가축

직접 3개월 이상 경험한 버티컬 도메인의 실제 사용자가 반복하는 업무를 해결하는 동작 가능한 Agent를 만든다. 단순 LLM 호출 래퍼에 그치지 않고 도메인 규칙·Tool·평가·정상/실패 사용자 흐름을 연결한다.

| 평가축 | 내용 | 배점 |
| --- | --- | --- |
| 문제 해결력 | 사용자 pain point와 solution 설계 | 25 |
| LLM 제어력 | 출력 계약·검증·재시도·모델 선택·실패 처리 | 25 |
| 서비스 완성도 | FastAPI·Docker·배포·사용성·장애 대응·재현 | 25 |
| 관측과 평가 | Langfuse 세 축·judge·비용과 품질 판단 | 25 |

### 핵심 기능 조건과 검증 방법

제공 가이드에서는 아래 6개를 미충족 시 해당 평가축 점수를 받지 못하는 핵심 조건으로 제시한다.

| ID | 공식 조건 | 검증 방법 / 제출 증거 |
| --- | --- | --- |
| P2-01 | 외부에서 동작 가능한 배포 URL. 로컬만으로 제출 불가 | 서비스 UI URL에서 정상 입력·결과·실패 안내 확인 |
| P2-02 | FastAPI + Docker, `.env.example` 기반 `docker compose up`으로 전체 서비스 재현 | clone 후 필요한 키를 입력하고 10분 안에 로컬 실행 가능한 README, Dockerfile/Compose, `/docs`, 요청·응답 Pydantic 모델 |
| P2-03 | 핵심 로직에서 LLM API 사용, Pydantic 출력 계약 + validation + retry + 최종 실패/fallback 처리 | 응답 schema·검증기·재시도 횟수/조건/repair prompt/포기 조건·최종 안내, **100건 이상 실행한 structured output 계약 준수율 실측** |
| P2-04 | Langfuse Observability / Prompt Management / Evaluation 모두 운영 | 아래 관측·프롬프트·평가 조건의 연결 증거 |
| P2-05 | Domain LLM + 자체 Skill + FastMCP 기반 MCP Server | 도메인 규칙·용어·판단 기준·예외·보류·검토된 노하우; 실제 데이터/동작 Tool, description·입출력 contract 및 Tool 분리 이유 |
| P2-06 | 별도 소개 페이지 + 팀 저장소 정리 + `.env.example`, 민감값 commit 금지 | 소개 URL, 정리된 저장소, 값 없는 환경변수 예시 |

### 공통 API·서비스 준비도

- `GET /health`: 상태 확인.
- `POST /api/agent`: 서비스 UI가 호출하는 Agent API; 요청·응답 예시를 README에 제공.
- `/mcp`: MCP client용 **Streamable HTTP** protocol endpoint. Agent API와 혼동하지 않는다.
- 공통 제출 구조는 Vercel/Next.js UI → Cloud Run/FastAPI → LLM·Domain API·MCP·Langfuse다. Frontend 선택 예시에는 Streamlit/Gradio/Flutter도 있으므로 Next.js만을 필수라고 단정하지 않는다. 제출 환경 예외는 최신 공지로 확인한다.
- MCP는 token·허용 client 등 접근 제어, 연결 방법, Tool 목록, 실제 호출 결과를 설명한다.
- 브라우저가 API를 직접 호출하면 CORS·인증·secret 비노출 방식을 README에 설명한다.
- request ID·model·token·latency를 구조화 로그에 남기고, UI에 입력 가이드·processing state·실패 후 다음 행동을 표시한다.
- LLM 호출을 하나의 service layer에 모으는 것은 가이드의 강한 설계 권고다.

### 모델 비교와 실패 경로

최소 **2개 이상 모델을 동일 입력 조건**으로 비교해 선택 근거를 남긴다. 품질·요청당 token/비용·**p50 / p95**·안정성(계약 준수율/실패율)을 측정한다. 상용 모델끼리 또는 상용과 허용된 로컬 SLM 비교가 가능하다.

SDK 사용도 계약 검증 책임을 면제하지 않는다. 구조화 출력·재시도·예외 처리 기본값을 왜 유지/변경했는지 설명한다.

| 실패 유형 | 설계·검증할 처리 |
| --- | --- |
| API timeout / 5xx | 제한된 retry, backoff, 최종 사용자 메시지 |
| schema 위반 | repair, retry, 최종 fallback |
| rate limit | 대기/큐/다른 모델 등 정한 정책 |
| 비용 초과 | 요청당 상한/차단 정책 |
| 부적절 입력 | 입력 검증/거부 |
| MCP/API 실패 | 상태 보존, 부분 실패와 전체 실패 구분 |

### Langfuse 관측·프롬프트·평가

- **Observability**: 모든 LLM 호출의 input/output, model, token, latency, cost, retry, `user_id`/`session_id`를 trace로 연결한다. 실제 사용자 데이터 전송은 팀 동의·비공개 정책을 지키며 식별자는 가명화한다.
- **Prompt Management**: Langfuse Prompt로 관리하고 version을 남긴다. 배포 없이 교체·rollback을 시연하며 trace에서 사용한 prompt version을 확인할 수 있어야 한다.
- **Evaluation / Dataset**: 최소 **30건 이상**, 정상·경계·실패 유도를 포함하고 각 case에 정답 또는 판정 기준과 이유를 기록한다. **Langfuse Dataset에 등록**하며 로컬 파일만으로 끝내지 않는다.
- 같은 Dataset으로 변경 전후 **두 번 이상** 측정하여 회귀 문항과 수치를 보고한다. 도메인 평가축은 2개 이상 분리한다. score에서 실제 judge trace까지 추적 가능하게 설계한다.
- LLM-as-judge의 생성 모델과 judge 분리는 제공 요약에서 권장이다. 기존 저장소 평가 안내와 `EVAL_REPORT.md`는 분리를 요구하므로 팀은 이를 유지한다. judge 점수는 독립 정답 근거를 대체하지 않는다.

### 계획서 보완 제출 조건

- 계획서는 LLM이 맡을 일과 코드 검증 책임, 범용 LLM만으로 부족한 이유, 조원 중 정답 판정 경험자가 있는지를 설명한다.
- 초기 평가 질문 **10건 = 정상 3 / 경계 4 / 실패 유도 3**. 경계 4개 중 **최소 3개는 실제 현장 경험이 있어야 정답을 낼 수 있는 질문**이어야 한다. 단순 합계·dictionary lookup만으로 대체하지 않는다.
- 각 case에 유형, 실제 입력 원문, 기대 출력/정답/판정, 판정 방식(코드/LLM/사람), 판정 이유·현장 기준, 범용 도구와의 차이, 판정한 조원을 기록한다. 예상 차이와 실제 도구 실행 결과를 구분한다.
- **평가 입력과 정답을 LLM으로 만들지 않는다.** 특히 LLM이 둘을 동시에 생성해 ground truth로 사용하는 것은 금지다. 형식 정리·초안 보조 가능성을 평가 문항/정답 생성 허용으로 확대하지 않는다. 최종 기준은 사람의 실제 경험·검토 또는 명시된 규칙 등 독립 근거가 필요하다. 허용되는 보조 범위는 강사에게 확인한다.
- 판정 불일치는 누가 어떻게 판단했는지 보존한다.
- 경험자가 없으면 그 사실을 숨기지 않고 착수 세션에서 범위를 조정한다. 외부 자문자의 경험을 팀원 경험으로 기재하지 않는다.

### 공식 기술 경계

- 필수: FastAPI, Docker/Compose, Langfuse, LLM 사용(OpenRouter/직접 vendor API 또는 허용된 로컬 SLM), 자체 Skill, MCP Server/FastMCP, GCP 배포 흐름.
- 선택 예: Next.js/Streamlit/Gradio/Flutter, Postgres 계열 DB 권장(Supabase 등 가능), LangChain, 조건부 vendor Agent SDK.
- **RAG 사용 금지**, **LangGraph 사용 금지**.
- RAG 판정: (1) 문서 chunk 더미 저장, (2) 질문마다 다른 chunk 조회, (3) 가져온 chunk를 prompt context에 넣어 생성 — 세 질문이 모두 Yes인 구조.
- 금지 예: PDF/규정집 청킹→vector DB→top-k→생성, 웹검색 본문을 context에 넣어 생성, 대화 이력을 청킹/검색해 복원, hybrid retrieval/reranking을 생성 context로 사용.
- 공식 허용 예: 고정 Skill 주입, MCP의 구조화 DB/API 값, 생성 context 검색이 아닌 임베딩 분류·라우팅·추천·중복 탐지, 유사 항목 목록 표시, 업로드 파일 1건 전체 처리.
- 위 허용 예가 말해봄 적용 승인은 아니다. 벡터 DB·임베딩 검색 등 더 좁은 팀 제외 범위는 [CONSTRAINTS](CONSTRAINTS.md)를 따른다.

### 제출 산출물과 마감

| 시점 (2026년, 제공 자료 표기) | 조건 |
| --- | --- |
| 9/18 금요일 오후 착수 전 | 계획서 보완 제출 |
| 9/23 | 문제 정의·범위·API/출력/관측 계약·30건 평가셋 초안/rubric 확정 흐름 권장; 기존 저장소 일정도 유지 |
| 9/30 중간 점검 | 문제 정의·평가셋·아키텍처·뺀 범위 확인 |
| **10/8 목요일 자정** | 코드·배포·리포트 마감. 이후 commit은 채점 미반영 |
| **10/11 일요일 자정** | 발표 PDF 마감. 10/9~11은 기능 추가가 아닌 발표 준비 |
| 10/12 월요일 | 발표 |

마감 시점 제출물은 서비스 UI URL, 소개 페이지 URL, Cloud Run Agent API와 health/agent 호출 예시, 10분 재현 README, 정리된 저장소·환경변수 예시·Docker 패키지, Skill, MCP 연결·Tool 목록·실제 호출·접근 제어, [EVAL_REPORT](../EVAL_REPORT.md), **Langfuse 스크린샷 3장 이상(trace 상세 포함)**, **정상 1개·실패 1개 데모 영상**이다. 발표 PDF는 위 별도 마감에 따른다.

발표에는 사용자 문제의 절실함, 제외 범위, 모델 선택 비교, schema 실패 동작, 평가셋 출처/규모/측정축, 개선 전후 수치, 요청 비용/p95, 가장 큰 약점을 근거로 답한다. 설계 원칙은 출력 계약·실패 경로·측정·비용/지연·범위 축소다.

## 프로젝트 적용 해석

아래는 기존 말해봄 기획의 적용 요구다. 공식 과제 전체의 공통 조건으로 일반화하지 않는다. 세부 자율 제약은 [CONSTRAINTS](CONSTRAINTS.md)가 canonical이다.

### 1. Functional Requirements

#### 연습 준비
- 검토된 지원 공고를 선택할 수 있어야 한다.
- 세션에서 공고 요구사항 1~2개를 선택할 수 있어야 한다.
- 선택한 공고·요구사항은 1차와 2차 답변에서 고정되어야 한다.
- 지원 범위 밖 질문은 임의의 기술 정답 판정으로 확장하지 않아야 한다.

#### 답변 수집
- 기존 녹음/STT/VAD 흐름을 재사용한다.
- 사용자가 STT 결과를 확인하고 필요한 부분을 수정할 수 있어야 한다.
- 확인된 텍스트는 revision으로 고정하고 문장 ID를 부여해야 한다.

#### 코칭
- 질문별 활성 기준으로만 답변을 평가해야 한다.
- 2026-09-28 사용자 요청 범위: 기본 질문 1~10번에 기존 고정 루브릭의 기준을 연결한다. 4번 외 질문에는 문제 해결 전용 기준을 요구하지 않는다.
- 공고 요구사항과 현재 답변의 관련성을 요구사항별로 보여줘야 한다.
- 항목별 상태·이유·실제 답변 인용을 제공해야 한다.
- 부족하거나 판단하기 어려운 항목을 구분해야 한다.
- 필요한 경우 확인 질문 1개를 제공해야 한다.
- 다음 연습 행동은 내용·전달력을 합쳐 최대 2개여야 한다.

#### 사실 확인
- 확인 응답은 원래 답변과 별도로 저장해야 한다.
- 미언급과 미경험을 구분해야 한다.
- 확인 응답을 원래 답변에 있었던 근거로 소급 사용하면 안 된다.

#### 재연습 비교
- 같은 공고·질문·기준으로 2차 답변을 분석해야 한다.
- 같은 기준 ID의 상태 변화와 양쪽 근거를 비교해야 한다.
- 설정이 다르면 비교를 막거나 같은 설정으로 재분석해야 한다.

### 2. Domain Requirements

문제 해결 경험 답변은 질문 의도에 따라 다음 기준 중 필요한 것만 사용한다.

- `problem_context` (C)
- `cause_observation` (O)
- `cause_inference` (I)
- `own_action` (A)
- `action_rationale` (D)
- `result_verification` (V)

상태는 다음 네 가지다.

- `met`
- `partial`
- `not_observed`
- `undetermined`

`not_observed`는 경험 부재를 의미하지 않는다.

### 3. MCP Requirements

운영 MCP는 최소 다음 읽기 도구를 제공한다.

- `get_question(attempt_id)`
- `get_job_context(attempt_id)`
- `get_job_competency(attempt_id)`
- `get_practice_attempt(attempt_id, revision_id)`
- `compare_attempts(previous_coaching_run_id, current_coaching_run_id)`

요구사항:
- 임의 SQL/임의 URL 실행 도구 금지
- 검증된 사용자 문맥 사용
- 소유자·유효기간·허용 ID 검사
- 연구용 원문/사례별 정답 비노출

### 4. Output Contract Requirements

최종 사용자 API는 최소 다음 개념을 가져야 한다.

- `status`
- `job_context`
- `job_alignment`
- `intent_assessment`
- `criterion_assessments`
- `evidence`
- `gaps`
- `clarifying_question`
- `next_actions`

상태:
- `ok`
- `needs_more_info`
- `unsupported`
- `unavailable`

형식 검증과 의미 평가는 구분한다.

### 5. Validation Requirements

서버가 자동 검증해야 할 최소 항목:
- 타입/필수 필드
- 허용 상태값
- 배열 길이
- 행동 개수
- 답변 revision
- 문장 ID와 실제 quote 일치
- 활성 기준 누락/중복
- 허용되지 않은 criterion ID
- 공고 requirement ID
- 공고/직무 정의 버전
- 행동 대상 ID

의미상 근거 일치와 코칭 적절성은 평가셋/사람 검토로 측정한다.

### 6. Evaluation Requirements

공식 평가 조건은 위 「Langfuse 관측·프롬프트·평가」와 「계획서 보완 제출 조건」을 적용하고, 실행 계획은 [evals/README](../evals/README.md)에서 관리한다.

- 기획의 ‘구현 후 확인 필요’ 4건은 공식 **경계** 4건에 대응하는 내부 후보명이다. 명칭만 대응시킨 것이며 현장 경험 조건 충족은 검토 전이다.
- 팀 계획은 품질 평가 30건(정상 9 / 경계 12 / 실패 유도 9), 계약 평가 **고유 입력 100건**이다. 공식 100건 이상 실행 조건과 고유 입력 수 조건을 구분한다.
- 같은 모델의 일반 피드백과 말해봄 방식, ChatGPT(GPT)·Gemini·Claude Code의 동일 입력 실제 출력을 비교하는 것은 팀 추가 계획이다. 가상 예시를 실측으로 사용하지 않는다.
- 개발 예제와 고정 평가셋을 분리하고 정답·기대 판정·평가 라벨을 생성 모델 입력에 넣지 않는다. 평가 변경 시 버전을 분리한다.

### 7. Observability Requirements

공식 trace 항목에 팀은 Skill 버전, 가명화된 사용자·세션 식별자, MCP/검증/저장 단계 연결을 추가한다. Prompt 버전은 공식 요구와 연결한다.

### 8. Data/Privacy Requirements

- 사용자 음성·전사문·확인 응답은 비공개
- 실제 원문을 공개 저장소에 넣지 않음
- 운영 기록 24시간 정책을 자체 데이터 수집 때문에 자동 연장하지 않음
- 연구/평가용 실제 사례는 별도 동의가 있는 경우만 분리 보관
- 연구용 사례의 목적·접근자·보관 종료일·철회 절차를 정함
- 모델 학습/Voice Cloning에 사용하지 않음

### 9. Deployment/Submission Requirements

기존 기획의 제출 증거 후보는 위 공식 제출 목록으로 대조한다. 기존 GPU/음성 자산의 코드·배포 설정은 정적 조사했으며 실행·재사용 품질은 별도 확인하고, 공식 재현 조건 충족을 현재 단정하지 않는다.

## 현재 상태

공식 조건은 **모두 충족 검증 전**이다. 현재 저장소에는 이관된 앱·음성 분석·인증·저장 코드와 일부 에이전트 스캐폴드가 공존한다. 정적 조사 결과는 [CURRENT_STATE](CURRENT_STATE.md)를 따른다. 문서·양식·endpoint 이름의 존재를 실행 증거로 사용하지 않는다.

- 제공 기획상 팀원 전원 면접관 경험이 없다. 도메인 3개월 경험 근거, 정답 판정 담당, 외부 검토 범위 및 경계 3건의 현장 경험 요건은 확인 필요다.
- 기획의 PS-01~10은 후보이며 공식 제출용 정답·판정 출처가 확정된 10건으로 간주하지 않는다.
- 계약 준수율·모델 비교·Dataset 등록·rollback·배포·재현 증거는 아직 없다.

## 검증 방법과 미확인 조건

각 조건의 검증 결과에는 파일/실행 경로, 실행일, 환경·모델·Prompt·Skill·Dataset/grader 버전, 분모/분자, 로그·화면·결과 위치를 연결한다. 기능 Spec은 [예시](specs/_example.md)의 Why/Goal/What/How/AC 형식을 사용하고, 결과는 [평가 리포트](../EVAL_REPORT.md), 실행 맥락은 [Worklog](worklogs/README.md)에 남긴다.

다음은 후속 확인이 필요하다.

1. 최신 Checkpoint/강사 공지와 PDF/DOCX 원문 변경 여부, 보완 제출 승인 상태.
2. ‘자정’의 정확한 cutoff·시간대·제출 채널 및 main 태그 운영. 제공 표기를 임의로 00:00/23:59로 변환하지 않았다.
3. 공통 Vercel/Cloud Run 구조와 선택 가능한 frontend·허용 로컬 SLM의 제출 예외 조건.
4. 팀의 도메인 경험과 경계 사례 판정 요건, LLM 형식 보조 허용 범위. 외부 자문이 팀 내 경험자 조건을 자동 충족하지 않는다.
5. 공식 100건 이상 실행의 입력 중복·반복/재시도 집계 세부 기준. 팀은 고유 입력 100건과 시도 수를 따로 기록하며 기준 충족을 추정하지 않는다.
