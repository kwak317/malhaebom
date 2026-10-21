# 전사 확정과 운영 코칭 연결

## Why

현재 분석 완료 직후 읽기 전용 전사문과 기존 내용 피드백을 표시한다. 사용자가 오인식을 고친 확정 답변을 만들 수 없고, 일반 연습 화면은 `/api/agent`와 연결되지 않는다. 코칭 API도 명시적 Mock 외에는 공급자·Supabase 문맥·MCP 호출 경로가 없어 운영 설정에서 `unavailable`을 반환한다.

## Goal

사용자가 STT 전사문을 수정·확정해 불변 `answer_revision`을 만든 뒤, 그 revision만 근거로 고정 Skill·MCP·LLM 코칭을 실행하고 일반 결과 화면에서 검증된 근거와 부족 항목을 확인하게 한다.

## What

- 완료·미만료 분석 작업에만 연결되는 불변 `answer_revisions` 테이블과 사용자 소유 RLS를 추가한다.
- `POST /analysis-jobs/{job_id}/answer-revisions`로 전사문을 확정하고 서버가 문장 ID를 만든다.
- 운영 MCP 서버가 Supabase의 확정 답변, 연습 세션의 선택 공고·요구사항, 서버 질문 카탈로그를 읽게 한다.
- FastAPI 코칭 서비스가 짧은 내부 MCP 토큰을 발급하고 실제 MCP stdio 도구 3개를 호출한다.
- OpenAI 호환 공급자(OpenRouter 포함)가 고정 Skill과 MCP 문맥으로 구조화 JSON을 생성한다.
- 기존 Pydantic ID·인용 검증을 통과한 결과만 저장·반환한다.
- 일반 결과 화면에 전사 편집·확정과 코칭 호출을 연결하고 `/demo/coaching` 의존을 제거한다.

## Data boundary

- 브라우저는 원문 답변, 사용자 ID, 공고 원문을 `/api/agent`에 보내지 않는다.
- 코칭 입력은 `question_id`, `answer_revision_id`, `job_snapshot_id`만 허용한다.
- MCP 내부 토큰에는 사용자와 허용 ID·읽기 scope·짧은 만료만 포함한다.
- Supabase service-role 키와 LLM 키는 서버 및 MCP 프로세스에서만 사용한다.
- 질문·전사·공고 내용은 지시가 아니라 판단 대상 데이터로 처리한다.

## Dependency

공고 선택 단계가 만드는 `practice_sessions`, `job_postings`, `job_requirements`, `practice_session_requirements` 레코드를 문맥 원본으로 사용한다. 이 변경은 해당 공고 선택 마이그레이션과 함께 배포해야 한다.

## Acceptance criteria

1. 완료되지 않았거나 만료됐거나 다른 사용자의 분석 작업은 전사 확정이 거절된다.
2. 확정 시 1~5000자의 텍스트를 서버가 문장으로 나누고, 새 revision을 만들며 기존 revision을 수정하지 않는다.
3. 코칭은 확정된 revision만 조회하고 원래 STT 텍스트를 근거로 사용하지 않는다.
4. MCP 도구는 내부 토큰의 사용자·scope·question/revision/job ID를 모두 검사한다.
5. 운영 모드는 Supabase 문맥과 실제 MCP 호출을 사용하며 demo fixture로 자동 대체하지 않는다.
6. LLM 출력의 요구사항 ID·기준 ID·문장 ID·정확 인용이 서버 문맥과 다르면 사용자에게 반환하지 않는다.
7. 질문·공고·revision이 같은 연습 세션에 속하지 않거나 만료되면 코칭 전에 차단한다.
8. 일반 결과 화면은 전사 수정 → 확정 → 코칭 로딩 → 근거·부족 항목·확인 질문·다음 행동 순서로 표시한다.
9. LLM/MCP/Supabase 설정이 없거나 실패하면 근거 없는 임시 피드백 대신 명시적 실패 상태를 보여준다.
