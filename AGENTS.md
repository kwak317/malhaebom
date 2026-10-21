# AGENTS.md

AI 코딩 에이전트(Claude Code, Codex, Cursor 등)가 이 저장소에서 작업할 때 따르는 공통 지침입니다. 어떤 도구를 쓰든 이 문서를 기준으로 합니다.

## Mandatory Preflight (작업 시작 시 필수 확인)

모든 AI 코딩 에이전트와 작업자는 작업을 시작하기 전 다음 6대 원칙을 반드시 확인하고 준수한다.

1. **작업 전 필수 문서 확인**: 작업 착수 전 `docs/PROJECT_OVERVIEW.md`, `docs/CURRENT_STATE.md`, `docs/TARGET_STATE.md`, `docs/REQUIREMENTS.md`, `docs/CONSTRAINTS.md`를 순서대로 확인한다 ([상세 1절](#1-작업-전-필수-확인)).
2. **하나의 작업 = 하나의 목적**: 한 PR과 한 브랜치는 하나의 명확한 논리적 목적만 다룬다 ([상세 9절](#9-git브랜치커밋-규칙), [10절](#10-pr리뷰merge-규칙)).
3. **기존 변경 보존 & 강제 리셋 금지**: 작업 전 `git status`를 확인하고 미커밋 변경을 보존한다. `git reset --hard`, `git checkout -- .`, `git clean -fd` 등 파괴적 명령을 절대 쓰지 않는다 ([상세 2절](#2-기존-프로젝트-보호-원칙), [9절](#9-git브랜치커밋-규칙)).
4. **테스트 통과 & Worklog 필수**: 테스트 통과 없이 완료로 보고하지 않으며, 의미 있는 작업 종료 전 `docs/worklogs/` 작성을 누락하지 않는다 ([상세 체크리스트](#작업-완료-체크리스트), [8절](#8-worklog-작성-규칙)).
5. **PR Review-size 정책 준수**: `400 LOC`는 무조건적 hard limit이 아니라 기본 **review-size guideline**이다. 리뷰 핵심 변경(review core: 코드, 테스트, 설정, Spec, 실험 계획/기준/절차 등)은 400줄 안팎을 권장하며, 예외/증빙 파일(Worklog, raw 실험 데이터, lockfile 등)을 포함해 400줄을 초과하더라도 하나의 논리적 작업이면 인위적으로 쪼개지 않는다. 단, 400줄 초과 시 PR 설명에 이유를 명시하고 논리적 커밋으로 분할한다 ([상세 10절](#10-pr리뷰merge-규칙)).
6. **다른 팀원 승인 후 작성자 최종 merge**: 팀원 1명 이상의 승인(approve) 없이 merge하지 않으며, 최종 merge는 작성자가 직전 상태를 검증한 후 직접 수행한다 ([상세 10절](#10-pr리뷰merge-규칙)).

---

## 프로젝트 개요

`말해봄 Mk.2`는 신입 개발자 취업준비생의 한국어 면접 답변을 녹음하고,
STT·VAD와 도메인 Skill·MCP·LLM을 이용해 답변 근거에 맞는 코칭과 재연습
전후 비교를 제공하는 버티컬 도메인 에이전트다. 2차 프로젝트에서는 RAG를
사용하지 않는다.

초기 제품 범위는 지원 공고와 프로젝트 문제 해결 경험을 연결하는 신입 백엔드 면접 코치다. 현재/목표 구조는 [아키텍처](docs/ARCHITECTURE.md)에서 구분한다.

## 기술 스택

- 프런트엔드: React, TypeScript, Vite, Nginx
- API: Python 3.12, FastAPI, Pydantic
- 음성 분석: faster-whisper, Silero VAD, 별도 GPU TTS Worker
- 인증·저장: Supabase Auth, Database, Private Storage
- 목표 에이전트: 고정 Skill, MCP, LLM 서비스, Langfuse (현재 구현과 구분)
- 배포: Docker Compose; 프런트엔드는 Vercel 분리 배포도 지원

## Spec 먼저, 구현은 그다음

기능을 에이전트에게 시키기 전에 `docs/specs/{기능명}.md`에 Spec을 먼저 작성하세요. 형식은 `docs/specs/_example.md` 참고 — 다섯 섹션(Why · Goal · What · How · AC)이 다 있어야 에이전트에게 그대로 넘길 수 있습니다.

- **Why**: 페르소나·상황·문제·측정 지표
- **Goal**: 숫자로 된 성공 기준 + Out of Scope
- **What**: Happy Path + Edge Case
- **How**: API·데이터·제약 (에이전트가 임의 결정할 여지를 없앤다)
- **AC**: Given-When-Then 형식, 테스트 코드로 바로 옮길 수 있어야 함

## Out of Scope 원칙

에이전트는 Spec에 없는 기능을 임의로 추가하지 않습니다. "이왕이면"으로 범위를 넓히지 않습니다.

## 완료 기준

테스트(AC 기준) 통과 없이 "완료"라고 보고하지 않습니다.

### 작업 완료 체크리스트

의미 있는 코드·설정·문서 변경을 완료하거나 commit/push/PR 하기 전에 반드시 확인한다.

- [ ] 관련 테스트·검증을 수행하고 결과를 확인했다.
- [ ] `docs/worklogs/`에 새 Worklog를 작성하거나 기존 Worklog를 갱신했다.
- [ ] Worklog에 변경 파일, 검증 결과, 실패·미확인 사항, 다음 작업을 기록했다.
- [ ] 이번 작업이 `docs/project2-checkpoint-work-cards.md`의 항목을 충족하거나 상태를 바꾸면, 같은 변경에서 해당 항목을 `[x]` / `[-]` / `[ ]` 상태로 갱신하고 필요한 증거 문서를 연결했다.
- [ ] 필요한 경우 `CURRENT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`를 갱신했다.
- [ ] commit/push/PR에 필요한 문서 변경까지 함께 포함됐는지 확인했다.

체크포인트 항목은 단순히 구현이 존재한다는 이유만으로 완료 처리하지 않는다. 해당 항목의 완료 조건을 실제로 검증했을 때만 `[x]`로 바꾸며, 완료 항목에는 근거 파일·문서·실험 위치를 짧게 적는다. 기반 구현은 있으나 운영 검증·증거가 부족하면 `[-]`를 유지하고, 아직 부족한 검증이나 증거를 한 줄로 적는다. 체크포인트와 무관한 작업은 억지로 체크리스트에 연결하지 않는다.

상세 형식과 병합 원칙은 아래 **Worklog 작성 규칙**을 따른다.

## 말해봄 프로젝트별 작업 규칙

## 1. 작업 전 필수 확인

작업을 시작하기 전에 다음 문서를 순서대로 읽는다.

1. `docs/PROJECT_OVERVIEW.md`
2. `docs/CURRENT_STATE.md`
3. `docs/TARGET_STATE.md`
4. [공식 요구사항과 프로젝트 적용 해석](docs/REQUIREMENTS.md)
5. `docs/CONSTRAINTS.md`

도메인 판단을 수정하면 `skills/interview-coach/SKILL.md`, 구조를 수정하면 `docs/ARCHITECTURE.md`, 평가 코드를 수정하면 `evals/README.md`도 읽는다.

공식 조건은 `docs/REQUIREMENTS.md`, 팀 자율 제약은 `docs/CONSTRAINTS.md`를 기준으로 구분한다. [수업 지식](docs/knowledge/COURSE_KNOWLEDGE.md)은 교육·기술 참고이며 신규 기능 요구나 구현 증거가 아니다. 평가 입력·정답은 LLM으로 생성하지 않으며 독립 판정 근거를 확보한다.

## 2. 기존 프로젝트 보호 원칙

- 이 저장소는 말해봄 2차 프로젝트의 메인 저장소이며, 기존 1차 코드는 PR #1로 이관되었다. 코드 존재와 실제 실행 검증은 구분한다.
- 추가 이관 승인이 없으면 다른 저장소의 코드를 찾거나 가져오지 않는다. 아래 규칙은 현재 이관된 코드에 적용한다.
- 기존 STT, VAD, TTS, 녹음, 전달력 분석, 인증, 저장 구조는 먼저 재사용 가능 여부를 확인한다.
- 기존 기능을 재작성하거나 제거하기 전에 실제 호출 경로와 의존성을 코드에서 확인한다.
- 기획 문서에 언급됐다는 이유만으로 코드에 구현되어 있다고 가정하지 않는다.
- 현재 구현을 확인한 사실은 `docs/CURRENT_STATE.md`에 반영한다.
- 죽은 코드, 실험 코드, 배포 코드가 섞여 있으면 구분해서 기록하고 임의로 삭제하지 않는다.

## 3. 고정 범위

- 대상: 신입 백엔드 개발자 준비생.
- 초기 면접 유형: 프로젝트 문제 해결 경험 한 유형.
- RAG, LangGraph, 임베딩/문서 조각 검색을 추가하지 않는다.
- 새로운 STT/TTS 학습을 MVP 제품 범위에 넣지 않는다. 다만 2026-09-19 사용자 승인으로 기존 adapter weight 유실에 대응하는 STT retrain은 별도 `experiment/` 범위에서만 수행할 수 있으며, 제품 기본 모델 교체는 별도 평가·결정 전까지 금지한다.
- 합격 가능성, 전체 직무 역량, 성격·채용 적합성을 판정하지 않는다.
- 사용자가 말하지 않은 역할·수치·성과·기술을 만들어내지 않는다.
- 확인 질문은 최대 1개, 내용·전달력 다음 행동은 합계 최대 2개를 유지한다.

자세한 제한은 `docs/CONSTRAINTS.md`를 따른다.

## 4. LLM과 서버의 역할 분리

LLM은 의미 해석과 코칭 제안을 맡고, 서버가 확정적으로 검사할 수 있는 항목은 서버에서 처리한다.

서버 책임의 예:
- 인증·소유자·유효기간 검사
- 답변 버전·문장 ID 고정
- 공고/요구사항 ID 허용 여부 검사
- Pydantic 스키마 검증
- 인용 원문 일치 검사
- 기준 ID 중복/누락 검사
- 다음 행동 개수 제한
- 1차/2차 동일 기준 상태 비교
- 저장·버전·만료 관리

LLM이 임의로 출처 URL, 기업 요구사항, 사용자 ID, 모델 ID, 권한을 생성하거나 확정하지 못하게 한다.

## 5. 데이터·평가 오염 방지

- 외부 검토자의 사례별 정답을 운영 LLM 입력에 넣지 않는다.
- 평가 구분, 기대 판정, 통과/실패 라벨을 모델 입력에 넣지 않는다.
- 개발 예제와 고정 평가셋을 분리한다.
- 실제 사용자 사례를 자동으로 Langfuse Dataset이나 공개 저장소에 올리지 않는다.
- 운영 기록과 별도 동의한 연구용 사례를 분리한다.

## 6. 변경 시 문서 갱신

- 현재 동작 변경 → `docs/CURRENT_STATE.md`
- 목표 범위 변경 → `docs/TARGET_STATE.md`
- 요구조건 추가/삭제 → `docs/REQUIREMENTS.md`
- 제외 범위/제약 변경 → `docs/CONSTRAINTS.md`
- 판단 규칙 변경 → `skills/interview-coach/SKILL.md`
- 서비스 경계/데이터 흐름 변경 → `docs/ARCHITECTURE.md`
- 일정/순서 변경 → `docs/IMPLEMENTATION_PLAN.md`
- 평가셋/지표 변경 → `evals/README.md`
- 중요한 선택 변경 → `docs/DECISIONS.md`

중요한 방향 변경을 코드만 수정한 채 남기지 않는다.

## 7. 작업 방식

- 한 작업에서 가능한 한 하나의 목적만 변경한다.
- 기존 테스트가 있으면 먼저 실행하고, 변경 후 회귀 테스트를 추가한다.
- 모호한 요구사항을 코드로 임의 확정하지 않는다. `TODO` 또는 결정 항목으로 기록한다.
- 문서와 코드가 충돌하면 코드의 실제 동작을 조사한 뒤 차이를 기록한다. 기획 문서를 근거로 실제 동작을 덮어쓰지 않는다.
- 새 의존성 도입 시 이유와 버전 고정 여부를 기록한다.
- 보안·권한·삭제·만료 경로를 정상 경로와 동일하게 검증한다.

## 8. Worklog 작성 규칙

의미 있는 코드·설정·문서 변경을 수행한 작업은 종료 전에 `docs/worklogs/`에 Worklog를 남긴다.

- 파일명 권장: `YYYY-MM-DD_HHMM_<short-title>.md`
- `docs/worklogs/TEMPLATE.md`를 기본 형식으로 사용한다.
- Worklog에는 추측이 아니라 실제 확인·수행·검증한 내용을 적는다.
- 변경 파일, 테스트 명령과 결과, 실패/미해결 사항을 숨기지 않는다.
- 같은 원인의 연속 작업은 기존 Worklog를 갱신할 수 있으나, 목적이 달라지면 새 Worklog를 만든다.
- `CURRENT_STATE`, `ARCHITECTURE`, `DECISIONS` 등 기준 문서 갱신이 필요한 변경은 Worklog만 남기고 끝내지 않는다.

### 문서 병합 원칙

이 문서 패키지를 기존 저장소에 반영할 때 동일하거나 유사한 문서가 이미 존재하면 새 파일을 무조건 추가하지 않는다.

1. 기존 파일의 역할과 내용을 먼저 읽는다.
2. 기존 문서가 같은 역할을 한다면 그 문서를 canonical 문서로 유지하고 필요한 내용만 병합한다.
3. 중복 문서를 새로 만들기보다 기존 디렉터리·명명 규칙을 우선한다.
4. 기존 README, AGENTS/CONTRIBUTING, docs 구조를 임의로 덮어쓰지 않는다.
5. 병합으로 경로나 파일명이 달라졌다면 문서 간 링크와 `AGENTS.md`의 참조 경로를 함께 수정한다.
6. 판단이 필요한 충돌은 임의로 삭제하지 말고 Worklog와 `docs/DECISIONS.md`에 기록한다.

**의미 있는 작업을 수행한 뒤 Worklog를 작성한다.** 위치: [docs/worklogs/](docs/worklogs/README.md). 목적·작업 전 상태·수행 내용·주요 판단과 이유·변경 파일·검증·발견한 문제·미확인 사항·다음 작업을 기록한다.

## 9. Git·브랜치·커밋 규칙

이 문서는 개발·Git/PR·Issue·CI 운영 규칙의 canonical entry point다. 아래 규칙은 팀 운영 정책이며 공식 과제 조건과 구분한다.

- 기본 브랜치에서 직접 기능 작업하지 않는다. `main`에 직접 push하지 않고 작업 브랜치 → PR → 리뷰 → merge 흐름을 따른다.
- 모든 작업 브랜치는 `<type>/<작업명>`, 모든 commit message는 `<type>: <summary>` 형식을 사용한다.
- 허용 type은 `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `experiment`다. `experiment/`는 모델 실험·benchmark·fine-tuning에 사용한다.
- 브랜치 예: `feat/job-posting-analysis`, `fix/stt-timeout`, `docs/experiment-rules`, `refactor/coaching-service`, `test/mcp-contract`, `experiment/tts-finetune-v2`.
- 커밋 예: `feat: add job requirement evidence mapping`, `fix: handle empty stt transcript`, `docs: add experiment reproducibility rules`, `test: add mcp contract regression cases`, `experiment: reproduce baseline tts benchmark`.
- 하나의 commit에는 가능한 한 하나의 논리적 변경만 포함한다. 본인 계정으로 커밋하고 공동 작업자는 `Co-authored-by:`로 기록한다.
- 작업 전에 status/diff를 확인하고 기존 uncommitted 변경을 보존한다. 관련 파일만 선별하여 stage한다. 다른 작업을 제거하는 `git reset --hard`, `git checkout -- .`, `git restore .`, `git clean -fd`를 사용하지 않는다.

## 10. PR·리뷰·merge 규칙

- 하나의 PR은 하나의 명확한 목적을 가진다.
- **Review-size 가이드라인 및 Review Core**:
  - `400 LOC`는 무조건적인 PR hard limit이 아니라 기본적인 **review-size guideline**으로 사용한다.
  - 코드, 테스트, 설정, 핵심 Spec, 실험 계획/평가기준/재현절차 문서 등 실제 리뷰 대상이 되는 핵심 변경(**Review Core**)은 가급적 **400줄 안팎**으로 유지한다.
  - `Worklog`, raw benchmark 결과 데이터(`local-results/`, `evals/results/`, `.jsonl` 등), `lockfile`, machine-generated artifact 등은 Review Core와 구분할 수 있다. 단순히 `docs/experiments/**`에 위치한다는 이유만으로 Review Core에서 제외되지 않는다.
  - 하나의 논리적 작업이라면 예외/증빙 문서나 부수 파일로 인해 전체 PR이 400줄을 다소 넘는다는 이유만으로 기계적으로 분할하지 않는다. 단순히 줄 수를 맞추기 위한 인위적인 PR 분할은 금지한다.
  - 큰 작업은 우선 **논리적인 commit 단위**로 나누어 리뷰어가 commit별로 순차적으로 검토할 수 있게 한다.
  - Review Core 자체가 매우 큰 경우(예: **800줄 이상**)는 기능 또는 책임 단위로 PR 분리를 우선 검토한다.
  - Review Core가 400줄을 초과하거나 전체 작업이 큰 경우, **PR description에 변경 크기, 이유, 별도 PR로 분리하지 않은 이유**를 명시해야 한다.
- merge 전 **다른 팀원 최소 1명의 승인**이 필요하다. 본인의 자기 PR 승인은 유효하지 않다.
- `CHANGES_REQUESTED` 또는 unresolved review comment가 남아 있으면 merge하지 않는다.
- 리뷰어는 승인·피드백을 담당하고, **PR 작성자가 자신의 PR을 최종 merge**한다. 작성자는 merge 직전 최신 상태·테스트·CI 결과를 다시 확인한다.
- 작성자 부재 또는 merge 불가 등 예외 상황에서만 다른 팀원이 대신 merge한다. 이유를 PR 또는 Worklog에 남긴다.

## 11. GitHub Issues 관리

기능상의 문제나 버그를 발견하면 먼저 기존 중복 Issue를 확인하고 GitHub Issues에 기록한다.

등록 대상:

- 요구사항과 다른 동작, 기존 정상 기능의 regression, 특정 입력에서 재현 가능한 오류.
- STT/TTS/LLM pipeline의 재현 가능한 기능 문제, API/MCP contract 위반.
- 로컬과 배포 환경의 기능 차이, 지금 고치지 않더라도 추후 해결할 기능적·기술적 문제.

단순 아이디어·사소한 오탈자·개인 메모까지 모두 Issue로 만들 필요는 없다. Issue에는 가능한 한 문제 요약, 발견 환경, 재현 절차, 기대 동작, 실제 동작, 로그/오류, 관련 trace/screenshot, 영향 범위, 임시 workaround를 남긴다. 민감값이나 사용자 원문은 공개하지 않는다.

해결 PR은 `Fixes #123` 또는 `Closes #123`처럼 Issue를 연결한다. 현재 PR과 관계없는 버그는 범위를 키우지 말고 별도 Issue로 분리한다. Issue 생성이 작업 범위에서 금지된 경우 실제로 생성하지 않고 Worklog에 발견 내용과 등록 필요를 남긴다.

## 12. 실험 재현성과 STT/TTS

모델 학습·fine-tuning·benchmark·모델 비교는 다른 팀원이 재현할 수 있어야 한다. 수행 전 [실험 상세 규칙](docs/experiments/README.md)을 반드시 읽고, 의미 있는 실험마다 환경·코드·모델·데이터·설정·실행 방법·평가·결과를 기록한다. 재현 방법 없는 GUI 수동 실행은 최종 실험 결과로 인정하지 않는다. 실험 기록과 Worklog를 서로 연결한다.

STT/TTS는 기존 자산·환경 조사와 checkpoint benchmark 재현으로 baseline을 확정한 뒤, 별도로 승인된 경우에만 신규 데이터로 fine-tuning한다. 기존 train 데이터 재투입과 held-out/benchmark/final test의 학습 사용을 금지한다. 모델 선택은 validation, 최종 평가는 test로 분리하며 동일 benchmark로 회귀까지 비교한다.

신규 STT/TTS 학습의 MVP 제외 원칙은 유지한다. 2026-09-19 승인된 Whisper Medium STT retrain은 예외적으로 별도 실험 범위에서 수행하며, [STT retrain Spec](docs/specs/stt-finetuning-retrain.md)과 [실험 기록]([REDACTED].md)을 따른다. 이 승인은 제품 기본 모델 교체나 TTS 신규 학습까지 확대되지 않는다.

## 13. GitHub Actions 자원 보호

- 일반 PR CI에서 전체 ML 학습 환경을 설치하지 않는다. PyTorch, CUDA packages, STT/TTS training dependencies, 대형 ML framework는 해당 job이 실제로 필요로 할 때만 설치한다.
- 의존성은 목적별 분리를 권장한다. 예: `requirements/base.txt`, `dev.txt`, `stt.txt`, `tts.txt`, `training.txt`. 이는 향후 구현 시 검토할 구조이며 현재 파일/디렉터리의 존재나 재구성을 뜻하지 않는다.
- 일반 CI에서 Hugging Face 대형 모델, STT/TTS checkpoint, 음성 학습 데이터, benchmark corpus, GB 단위 artifact를 자동 다운로드하지 않는다. mock·fixture·small sample을 우선한다.
- 기본 PR gate는 lint, unit test, schema test, contract test, lightweight integration test를 중심으로 설계한다. 이 통과를 실제 모델 품질 검증으로 표현하지 않는다.
- real STT/TTS inference, GPU test, full benchmark, fine-tuning은 별도 heavy validation으로 분리한다. 필요에 따라 manual workflow, scheduled workflow, dedicated runner 또는 local reproducible experiment로 수행하고 결과를 실험 문서/Worklog에 남긴다.
- 반복 dependency 설치에는 package manager cache를 우선 검토한다. requirements 또는 lockfile hash를 cache key에 포함해 의존성 변경과 무관한 반복 다운로드를 줄인다.
- job에는 합리적인 `timeout-minutes`를 설정하는 것을 원칙으로 한다. dependency download나 외부 서비스 장애로 장시간 대기하지 않게 한다.
- 같은 branch의 새 commit으로 이전 실행이 불필요해지면 `concurrency`와 `cancel-in-progress`를 활용해 중복 실행을 줄이는 것을 권장한다.
- `requirements*`, lockfile, Dockerfile, compose, GitHub Actions workflow, ML dependency 설정 변경 시 CI 다운로드량·실행 시간 영향을 확인한다. 특히 requirements 변경으로 일반 CI가 전체 ML dependency를 설치하게 되지 않았는지 반드시 확인한다.
- dependency 설치/다운로드가 비정상적으로 오래 걸리면 실패한 workflow를 무작정 rerun하지 않는다. 원인을 조사하고 dependency/workflow/cache 구조를 수정한 뒤 재실행한다.

## 14. 문서 정책과 기술적 강제의 구분

규칙은 문서 정책과 자동 기술적 검증으로 구분된다.

- **자동/CI 기술적 검증 (Automated Enforcement)**:
  - PR diff 크기 및 Review Core 분류 검사: `scripts/check_pr_policy.py` 및 `.github/workflows/pr-policy-check.yml` (Review Core 800줄 하드 리밋 차단, 400줄 초과 시 PR 설명 내 사유 섹션 포함 여부 검사 등).
  - Secret 누출 검사: `.github/workflows/secret-scan.yml` (gitleaks).
- **문서 정책 및 팀 프로세스 (Documented Policy)**:
  - GitHub branch protection, required approvals, 머지 권한 관리 등 GitHub 원격 저장소 설정은 관리자 권한이 필요하므로 문서 정책을 기준으로 운영한다.
  - LLM 평가 결과 불변, 도메인 판단 규칙, Worklog 성실 작성 등은 정량 지표 외 정성적 정책으로서 코드 리뷰와 문서 대조를 통해 준수한다.
