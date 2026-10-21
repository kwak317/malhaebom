# Worklog — 수업 지식·Project2 공식 요구사항 통합

- 일시: 2026-09-16 (Asia/Seoul)
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음; commit/push하지 않음
- 관련 요구사항/결정: 사용자 문서 통합 요청, [REQUIREMENTS](../REQUIREMENTS.md), [CONSTRAINTS](../CONSTRAINTS.md)

## 1. 목적

루트의 입력 자료 2개를 기존 문서 체계에 중복 없이 통합한다. 교육/기술 참고, 공식 과제 조건, 프로젝트 적용 해석, 팀 자율 제약을 구분하고 링크·평가 계획·Worklog의 정합성을 검증한 뒤 입력 파일을 제거한다.

입력 파일과 통합 전 SHA256:

- `COURSE_KNOWLEDGE.md`: `24dab967a9bb2eb3dca9496e463bf45ddf7e45b748d5755f40b0f0e7343fc073`
- `PROJECT2_REQUIREMENTS.md`: `c920ef7f8396e44a1714f339872c9c3c1d26982aa22303f2d702146f608c8bdf`

## 2. 작업 전 상태

앞선 bootstrap 작업의 미커밋 변경이 그대로 있었다. Git 기준 수정 4개(`README.md`, `AGENTS.md`, `skills/SKILL.md`, `evals/README.md`), 신규 문서 16개 및 이번 루트 입력 2개가 untracked였고 staging은 비어 있었다. 작업 시작 시 전체 tracked/untracked 파일 38개의 SHA256을 임시 기록하여 이번 작업과 이전 변경을 구분했다.

조사 결과:

- README: 프로젝트 문서 목차·이관 대기·협업 규칙이 있다.
- AGENTS: 필수 읽기 목록에 `docs/REQUIREMENTS.md`가 이미 있다. CLAUDE는 AGENTS 위임이므로 수정 불필요.
- `docs/REQUIREMENTS.md`: 말해봄 기획의 기능·MCP·계약·개인정보 조건은 있으나 공식 과제의 상세 증거·마감·보완 양식 조건이 부족했다.
- `docs/research/`: 경쟁·공고·면접 도메인 조사이며 일반 Agent Engineering 지식과 역할이 다르다.
- `skills/SKILL.md`: 면접 답변의 C/R/A/D/V 판단 규칙이다. 교육 지식을 섞지 않는다.
- `evals/README.md`: 팀 평가 계획은 있으나 공식 경계 명칭, 현장 경험 요건, Dataset 등록, 입력/정답 생성 금지, Prompt rollback 증거 보완이 필요했다.
- `docs/worklogs/`: 기존 안내·템플릿·첫 기록을 유지한다.
- `docs/knowledge/` 및 동일 역할 교육 지식 문서는 없었다.
- 기존 1차 코드 이관은 여전히 대기 상태이며 다른 저장소 코드 탐색·이관을 하지 않았다.

## 3. 수행 내용

### 수업 지식

`COURSE_KNOWLEDGE.md`를 `docs/knowledge/COURSE_KNOWLEDGE.md`에 통합했다. 기존 대문자 파일명 관례를 따르고 별도 knowledge README는 만들지 않았다. 원자료 위치·수업 보강 맥락과 기술 본문을 보존하되 bootstrap 지시를 문서 역할 안내로 바꿨다.

보존한 내용: 출력 계약/validation, Workflow/Agent/Tool 설계, MCP 역할/contract/권한/인증/테스트, FastAPI/Docker, Langfuse 세 축, state/session/long-term memory, context budget, compaction/selection, 긴 대화 품질 측정, prompt version/release/rollback, 말해봄 적용 참고.

모델·가격·UI·정책·SDK 예시는 고정 요구가 아니며 실제 적용 때 최신 자료를 확인하도록 표시했다. 11절의 공식 RAG/LangGraph 목록은 요구사항 canonical 참조로 통합했다. 장기 memory 설명은 현재 기능 추가 지시가 아님을 명확히 했다.

### 공식 요구사항

`PROJECT2_REQUIREMENTS.md`의 중복 체크리스트를 그대로 복사하지 않고 `docs/REQUIREMENTS.md` 안의 공식 조건·프로젝트 적용 해석·현재 상태·검증 방법으로 정리했다.

| 입력 자료 내용 | canonical 반영 위치 |
| --- | --- |
| 출처/해석/문서 관계 (0, 17절) | 출처와 해석 범위, 문서 역할 링크 |
| 정체성·평가축 (1, 2절) | 프로젝트 정체성과 평가축 |
| 일정·제출·체크리스트 (3, 14, 16절) | 제출 산출물과 마감, 핵심 조건별 검증 방법 |
| 필수 6개·서비스 준비도 (4, 12절) | P2-01~06 표 및 공통 API·서비스 준비도 |
| 공통 endpoint·기술 경계 (5, 6절) | `/health`, `/api/agent`, `/mcp`, 공식 필수/선택/금지 구분 |
| LLM·실패 처리 (7, 8절) | 계약 100건 이상 실측, 2개 모델 비교, 실패 경로 |
| Langfuse·평가 (9절) | 모든 LLM trace, Prompt 교체/rollback, Dataset 등록·동일 셋 재측정 |
| 보완 제출 (10절) | 정상 3/경계 4/실패 유도 3, 독립 정답, 경계 최소 3건 현장 경험, 판정자/불일치 |
| Skill/MCP (11절) | P2-05 및 공통 API의 Tool 계약·접근 제어·실제 호출 증거 |
| 설계 원칙·발표 질문 (13, 15절) | 제출 증거와 발표 준비 설명 |

기존 말해봄 기능·도메인·MCP 도구·출력 필드·검증·개인정보 조건을 보존했다. 공통 평가/관측/제출 조건은 공식 절을 참조하고 팀 추가 요구만 적용 해석에 남겼다.

## 주요 판단과 이유

- 요구사항 canonical은 기존 `docs/REQUIREMENTS.md`로 유지한다. `docs/PROJECT2_REQUIREMENTS.md`나 별도 공식 요구사항 문서를 만들지 않았다.
- 교육 지식은 요구사항/면접 Skill과 역할이 달라 knowledge 아래 하나만 만들었다. 루트 지식 복사본이나 research 내 지식 복사본은 만들지 않았다.
- 공식 금지인 RAG/LangGraph와 팀 자율 제약인 벡터 DB·임베딩 검색·장기 코칭 제외를 구분했다. 공식 허용이 팀 적용 승인으로 해석되지 않도록 했다.
- 공식 ‘100건 이상 실행’과 팀의 ‘고유 입력 100건’은 다른 조건이다. 최초/최종 준수율·입력 수·실행/재시도 수를 분리하도록 했다.
- ‘구현 후 확인 필요’는 기존 PS 경계 후보의 내부명으로 보존했지만 실제 현장 경험 요건을 충족했다고 보지 않았다.
- 입력 요약은 judge 분리를 권장으로 표현하지만 기존 평가 안내/리포트는 분리를 요구한다. 기존의 더 엄격한 팀 규칙을 유지하고 CONSTRAINTS에 기록했다.
- 평가 입력과 정답의 LLM 생성 금지를 완화하지 않았다. 형식 보조를 생성 허용으로 해석하지 않으며 허용 범위는 확인 필요로 남겼다.
- 공통 제출 구조의 Next.js 예시와 frontend 선택 허용을 구분하고, ‘자정’의 시각을 임의 확정하지 않았다.

## 4. 변경 파일

이번 작업 시작 상태 대비 기존 문서 8개 수정:

| 파일 | 변경 내용 |
| --- | --- |
| `README.md` | 지식 문서 링크, 요구사항 역할 설명 |
| `AGENTS.md` | 기존 필수 요구사항 경로를 링크화, 공식/팀/교육 역할과 평가 생성 금지 안내 |
| `docs/REQUIREMENTS.md` | 공식 조건 병합 및 기존 적용 해석 보존 |
| `docs/CONSTRAINTS.md` | 공식 금지와 자율 제약 구분, 기존 judge 분리 규칙 명시 |
| `docs/TARGET_STATE.md` | 공식 제출 조건 참조 및 평가 목표 정합성 |
| `docs/IMPLEMENTATION_PLAN.md` | 초기 경계 검수·Dataset·Prompt rollback·공식 마감 연결 |
| `evals/README.md` | 평가 출처·구성·등록·비교·준수율·Prompt 증거 실행 계획 |
| `docs/worklogs/README.md` | 이번 기록 링크 |

신규 2개: `docs/knowledge/COURSE_KNOWLEDGE.md`, 이 Worklog.

`CLAUDE.md`, `skills/SKILL.md`, 조사 문서, 원본 기획서, 과거 Worklog, `EVAL_REPORT.md`, 코드·설정·의존성·평가 데이터는 이번 작업에서 수정하지 않았다. 최종 Git status의 Skill 수정 표시는 이전 bootstrap 변경이다.

## 5. 검증

- 입력의 공식 조건을 위 절별 매핑으로 대조하고 기존 프로젝트 적용 요구 보존을 확인했다.
- 임시 Python 검증기로 수업 지식의 핵심 항목과 공식 조건의 주요 용어·수치, 요구사항/평가 계획의 3·4·3 구성·독립 정답·Dataset·100건·p50/p95·rollback 일관성을 검사했다.
- 운영 문서의 상대 Markdown 링크 60개를 실제 경로와 대조하여 통과했다. 원본 기획서의 기존 작성자 PC 링크 8개는 앞선 bootstrap에서 기록한 보존 예외이며 변경하지 않았다.
- 작업 시작 파일 해시와 비교하여 변경이 위 문서 8개 및 신규 2개로 제한됨을 확인했다. 비문서 파일과 기존 Skill·기획 원본은 동일하다.
- `git diff --check`와 신규/기존 Markdown 공백 검사를 통과했다.
- 통합 검증 후 루트 입력 2개를 삭제하고 `git ls-files --cached --others --exclude-standard`에 루트 입력이 남지 않았음을 확인했다. staging은 비어 있다.
- 기능 테스트·외부 API·배포·원자료 웹 재조회는 실행하지 않았다. 이번 검증은 문서 통합 AC 범위다.

## 6. 발견한 문제 / 남은 리스크

입력 자료도 Checkpoint live 재조회 실패를 명시한다. 이번 문서는 제공된 공식 조건 요약이며 최신 공지를 새로 확인했다는 뜻이 아니다. PDF/DOCX 대조 역시 입력 작성자의 설명으로 구분했다. 기존 기획의 PS 후보 및 팀원 면접관 경험 부재는 공식 현장 경험 조건과 대조가 필요하다.

## 미확인 사항

- 최신 Checkpoint/강사 공지·보완 제출 승인 상태.
- 정확한 마감 cutoff·시간대·제출 채널 및 main 태그 운영.
- 선택 frontend·허용 로컬 SLM·공통 배포 구조의 예외 조건.
- 도메인 3개월 경험 근거·판정 담당·경계 최소 3건의 현장 경험 요건·외부 검토 범위.
- LLM 형식 보조 허용 범위와 공식 100건 집계 세부 기준.
- 서비스 구현·배포·평가·Prompt rollback 실측 증거. 기존 코드 이관 대기 상태 유지.

## 7. 다음 작업

최신 공식 공지와 팀의 경험/판정 근거를 확인하고 초기 10건을 사람의 독립 근거로 검수한다. 구현은 별도 승인된 코드 이관과 baseline 확인 이후 기능 Spec/AC에 따라 진행한다. 이번에는 이관·구현·리팩터링·설치·DB 변경·배포·commit·push를 하지 않았다.
