# Implementation Plan

## 구현 원칙

기존 프로젝트의 음성·연습 자산을 먼저 실사하고 재사용한 뒤 새 코칭 계층을 추가한다. UI 전환이나 부가 기능보다 **도메인 기준·공고 연결·검증·평가**를 우선한다.

## 선행 상태 — 코드 이관 및 정적 audit 반영

PR #1로 기존 코드가 main에 반영되었다. 2026-09-17 정적 조사 결과는 [현재 상태](CURRENT_STATE.md), [음성 인수 기록](experiments/2026-09-17_voice-asset-intake.md)에 연결한다. 구현 존재 확인과 실행 검증을 별도 완료 조건으로 둔다.

## Phase 0 — Baseline Audit / 인수 검증

- [x] frontend/backend entrypoint·STT/VAD/TTS·기존 LLM 호출 경로 정적 확인
- [x] Supabase schema/RLS·만료·1차/2차 연결·Docker 설정 정적 확인
- [x] CURRENT_STATE·ARCHITECTURE 갱신
- [ ] 별도 승인 환경에서 의존성·checkpoint·데이터 접근 권한 확인 및 환경 재구축
- [ ] 기존 checkpoint benchmark 재현·baseline 확정 (신규 학습은 제외 유지)
- [ ] 로그인/녹음/저장/비교 E2E, 권한·만료·삭제 및 재시작 검증
- [ ] 정적 Issue 후보(비교 문구·만료 접근·Compose TTS 주소)를 별도 수정 작업으로 검토

완료 증거: 정적 근거는 확보. 실행 결과·baseline 수치는 아직 없음.

## Phase 1 — Domain/Data Grounding

- [ ] 팀 실제 개발 사례 3건 정리
- [ ] 신입 백엔드 실제 공고 3건 확보 경로 확인
- [ ] 공고 요구사항 1~2개 구조화 규칙 확정
- [ ] 외부 면접 경험자 검토 범위 확정
- [ ] 공식 초기 질문 정상 3/경계 4/실패 유도 3 및 경계 최소 3건의 현장 경험·독립 판정 출처 확인
- [ ] 판단 기준 카드 초안 작성
- [ ] Skill/criteria 구조 고정

완료 증거: 실제/변형/가상 출처가 구분된 사례와 검토 상태.

## Phase 2 — Core Text Coaching

- [ ] 공고 스냅샷/requirement 구조
- [ ] 답변 revision/문장 ID
- [ ] Skill 로딩
- [ ] 구조화 LLM 출력
- [ ] Pydantic 검증
- [ ] 인용 검증
- [ ] 공고 관련성 검증
- [ ] 확인 질문 1개/행동 2개 제한

완료 증거: 텍스트 입력으로 검증된 코칭 결과 생성.

## Phase 3 — MCP and Authorization

- [ ] FastMCP 연결
- [ ] `get_question`
- [ ] `get_job_context`
- [ ] `get_job_competency`
- [ ] `get_practice_attempt`
- [x] `compare_attempts` — 저장된 두 코칭 결과를 추가 LLM 호출 없이 비교하고 단위·HTTP MCP 테스트 통과
- [ ] 기존 JWT/RLS 경계를 재사용하고 MCP 소유자/만료/허용 ID 검사를 보완
- [ ] 타 사용자/만료 요청 차단 테스트

완료 증거: 실제 MCP trace와 권한 실패 테스트.

## Phase 4 — Confirmation and Re-answer Comparison

- [ ] 확인 응답 저장
- [ ] 사용자 진술 상태 저장
- [ ] 선택 행동 저장
- [ ] 기존 attempt_no/동일 질문 검사를 재사용하여 2차 답변 코칭 연결
- [x] 같은 criterion 상태 변화 계산 — `not_observed`/`undetermined`에서 `met`으로 바뀐 경우만 새 설명으로 분류
- [x] 양쪽 근거 표시 — 저장된 각 결과의 criterion evidence를 함께 반환
- [x] 비교 불가 조건 처리 — 사용자·만료·세션·질문·공고·model·Prompt·Skill 버전과 1차→2차 순서를 검증

완료 증거: 같은 공고/질문의 전후 비교 화면 또는 API 결과.

## Phase 5 — Existing Voice Integration

- [ ] 기존 녹음·STT/VAD·전달력·TTS 호출 경로를 재사용/수정하여 새 코칭 연결
- [ ] 자동 feedback/improved_answer 경로를 전사 확인·revision 확정 후 코칭으로 변경
- [ ] 전달력 지표와 내용 행동 합치기
- [ ] 내용 코칭 실패 시 전달력 결과 유지
- [ ] E2E 로그인→녹음→코칭→재녹음 비교

완료 증거: 배포 환경 E2E.

## Phase 6 — Observability and Evaluation

- [ ] Langfuse trace — v4 redacted smoke 수신은 확인, 실제 provider trace는 미확인
- [ ] Prompt/Skill 버전, Prompt 교체·rollback 시연 — candidate version 연결은 확인, production 승격·rollback은 미수행
- [ ] 모델 A/B
- [ ] 일반 피드백 기준선
- [ ] 30건 품질 평가와 Langfuse Dataset 등록·동일 셋 전후 재측정 — Dataset 30건 등록 완료, 실제 전후 재측정은 미수행
- [ ] 고유 입력 100건 계약 평가; 실행 수·재시도 수·준수율 분리 기록
- [ ] 실패 유도
- [ ] p50/p95/비용 측정
- [ ] `EVAL_REPORT.md`

## 일정 기준

공식 제출 마감·중간 점검·코드 동결은 [REQUIREMENTS](REQUIREMENTS.md)의 「제출 산출물과 마감」을 따른다. 아래는 이를 위한 팀 작업 계획이며 공식 일정의 대체 문서가 아니다.

기획 문서의 초안 일정:
- 9/17~9/18: 범위/담당/실제 사례/공고/자문 계획
- 9/21~9/23: 규칙 카드·평가셋·계약·모델 결정
- 9/28~9/30: 초기 배포·텍스트 코칭·MCP·Langfuse
- 10/1~10/2: 확인 응답·비교·음성 통합·모델 비교
- 10/6~10/8: 사람 검토 반영·회귀·권한·삭제·재현·동결
- 10/9~10/11: 발표 정리

최신 강사 공지와 팀 역할 합의에 따라 갱신한다.

## 일정 부족 시 축소 순서

먼저 축소:
1. 화면 장식
2. 추가 음성 재생 연결
3. 부가 편의 기능

유지:
1. 핵심 코칭
2. 공고/근거 연결
3. 권한/검증
4. 평가
5. 정상/실패 배포 검증
