# 비교 후 면접 대화

## Why
비교 후 보완 설명과 면접 표현에 대해 대화를 이어간다.
## Goal
첫 질문 1개, 매 응답 꼬리질문 최대 1개, 사용자가 종료하면 요약한다. 고정 턴 수 제한은 없다. 재채점·RAG·장기 저장·음성 대화는 제외한다.
## What
비교 완료 → 첫 질문 → 사용자 답변/질문 → 짧은 피드백과 질문 → 사용자 종료 → 연습 요약. 시작 409는 비교를 유지하며 대화 불가로 안내한다. 다른 실패는 재시도하고 진행 중 404/409는 새 대화로 복구한다.
## How
- `POST /api/agent/chat`: action=start|message|finish, request_id(UUID), practice_session_id, 후속 conversation_id, message 요청의 message.
- Bearer 필수. 서버가 사용자 JWT/RLS로 세션·검토 공고·두 확정 답변/코칭을 조회하고 기존 동일 기준 비교를 재사용한다. 원래 기록은 쓰지 않는다.
- 두 run의 model_name/prompt_version/skill_version/criteria_version이 모두 존재하고 같아야 한다. criteria_version은 코칭 저장 시 서버의 question 문맥에서 기록하며 현재 질문 버전과도 일치해야 한다. 과거 null 버전은 추정하지 않고 재분석을 요구한다.
- 서버가 `prompts/interview-conversation.md`의 역할·응답 형식과 `skills/interview-conversation/SKILL.md`의 질문·근거 판단을 결합하고 별도 출력 Schema를 모델에 보낸다. 형식 오류는 1회 repair. 기존 provider의 dict/CoachingProviderResult 모두 지원한다.
- 첫 질문은 2차 미보완 설명 우선, 충분하면 선택 이유/적용을 묻는다. 사용자 질문에 먼저 답하고 없는 경험·성과를 만들지 않는다.
- 단일 프로세스 메모리, 최근 메시지 12개+4000자 요약, 최대 출력 2048토큰. 새 시작 ID는 새 대화이며 성공한 요청의 ID/action/message/응답은 대화 수명 동안 보관한다. 이전 ID·같은 입력은 원래 응답을 재사용하고 같은 ID의 다른 입력/action은 거부한다. 실패한 생성은 성공 캐시에 넣지 않는다.
- 매 요청 소유자·최초 만료·revision 변경을 검사한다. 종료 후 메시지는 거부한다. 새로고침/재시작·다중 worker 간 복원은 지원하지 않는다.
- 대화 경로의 비용·토큰 누적 예산 및 generation 관측은 아직 연결하지 않는다. 기존 /api/agent의 예산·관측은 유지한다.
## AC
- Given 유효한 두 답변·코칭과 비교 완료, When start, Then 서버 문맥의 첫 질문과 ID를 반환한다.
- Given 진행 중, When 사용자 답변/질문, Then 짧은 응답과 질문 최대 1개이며 기존 판정은 불변이다.
- Given finish, Then 요약·다음 연습 반환, 질문=null이며 후속 메시지는 409다.
- Given 타 사용자·만료·삭제·기록 변경·비교 전, Then 모델 호출을 차단한다.
- Given 중복 성공 요청/실패 재시도, Then 응답을 재사용하거나 원래 상태를 유지한다.
- Given model/prompt/skill/실제 criteria 버전의 누락·불일치, When start, Then 모델 호출 없이 대화를 차단한다.
- Given A 성공 뒤 B 성공, When A 재전송, Then 원래 A 응답을 반환하며 턴·요약·모델 호출 수는 늘지 않는다. 같은 ID에 다른 입력/action은 거부한다.
