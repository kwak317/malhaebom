# 저장소 구현 점검표

이 문서는 PRD와 작업 우선순위 1–10을 기준으로 저장소의 구현·문서·테스트를 대조한 결과다. 날짜가 아니라 재현 가능한 현재 상태를 기준으로 한다.

## 구현 상태

| 범위 | 확인된 산출물 | 상태 |
|---|---|---|
| PRD와 범위 | `docs/prd.md`, 기획서, 기능 Spec | 구현 범위와 RAG 제외 경계 반영 |
| 코칭 입력 계약 | 질문·답변 revision·공고 snapshot ID 요청, JWT 사용자 기준 서버 조회 | 구현 및 테스트 있음 |
| 코칭 출력 계약 | Pydantic 8개 필드, 정확한 ID·인용 검증 | 구현 및 테스트 있음 |
| Mock 코칭 API | `/api/agent` 고정 JSON과 현재 계약 검증 | 구현 및 Compose E2E 있음 |
| MCP 도구 | 질문·현재 답변·검토 공고 조회, 소유권·만료 검사 | 구현 및 Compose E2E 있음 |
| 고정 Skill | `SKILL.md`, 문제 해결 질문 문서, `criteria.json`, 서버 버전 검사 | 구현 및 테스트 있음, 검토 상태 `team_draft` |
| 평가셋 | 합성 30건, 정상 12·경계 10·실패 8 | 구현 및 테스트 있음 |
| 프런트 연결 | 판정·근거·부족 항목·확인 질문·다음 행동 표시 | 구현 및 프런트 테스트 있음 |
| 관측·실패 | Langfuse 허용 metadata 계약, 공통 오류 상태 | 구현 및 테스트 있음 |
| Docker 재현 | frontend → Nginx → FastAPI Mock/MCP E2E | 구성과 자동 검증 있음 |
| 모델 비교 | 동일 평가셋의 계약 준수율·정확도·비용·p50·p95 runner | Mock 재현 가능, 실제 후보 실행 보류 |

## 이번 대조에서 수정한 누락

- 빈 `SKILL.md`를 실제 코칭 규칙으로 교체하고 질문 유형 문서와 기계 판독 기준 카탈로그를 추가했다.
- API Mock의 `problem_context`와 평가셋의 `situation`으로 나뉘었던 기준 ID를 `problem_context`로 통일했다.
- 질문 유형·기준 버전·활성 기준이 고정 Skill과 다르면 서버가 모델 호출 전에 거부하도록 했다.
- 모델 비교 결과에 prompt·Skill·criteria 버전과 Skill 묶음 SHA-256이 남도록 했다.
- Docker API가 호스트 GPU Worker를 가리키는 주소와 로컬 FastAPI 주소를 분리했다.
- 별도 GPU Worker를 질문 TTS의 입력 검증·소유권·비공개 저장·24시간 만료 흐름에 연결했다.
- Compose 프런트 빌드가 기존 공개 `SUPABASE_*` 값도 사용할 수 있게 했다.
- 녹음 화면이 기본 질문의 검수 WAV와 직접 질문 전용 스트리밍 API를 구분해 재생하도록 연결했다.
- 분석 API의 답변 길이·참고 기준·피드백 객체와 실제 History API가 연결된 현재 상태로 와이어프레임 문서를 갱신했다.
- TTS 문서를 질문자 10개 등록, 코치 90개 초안, 별도 코치 2개 로컬 검수라는 실제 메타데이터와 맞췄다.
- 기획서의 개인 컴퓨터 절대 경로 링크를 저장소 기준 링크 또는 출처 설명으로 바꿨다.

## 외부 결정·권한이 필요한 보류 항목

- 후보 LLM 선정과 실제 30건 반복 실행, 실행 시점 가격·정확도·p95 기록
- 외부 면접관의 기준 검토와 기대 판정 이견 기록
- 운영 Langfuse 프로젝트에서 실제 trace와 Prompt Management 버전 확인
- 팀 Supabase의 질문자 음성 자산·정책 연결과 코치 음성 업로드
- 배포 URL, 운영 secret, 실제 공고 snapshot 저장소 연결

이 항목은 파일 누락으로 완료할 수 있는 일이 아니므로 현재 완료로 표시하지 않는다. 모델이 정해지기 전에는 Mock과 고정 계약을 기준선으로 유지한다.

## 재현 확인

- Docker API 이미지에서 백엔드 단위·계약 테스트 167개 통과
- 프런트 단위 테스트 22개와 production build 통과
- 30건 평가셋을 `mock:expected`, `mock:degraded` 두 후보로 실행하고 Skill·criteria 버전과 묶음 SHA-256이 결과에 남는지 확인
- Compose의 frontend, FastAPI, 별도 GPU TTS Worker health와 API 컨테이너에서 Worker까지의 연결 확인
- 브라우저에서 홈과 질문 선택 화면을 열어 빈 화면·오류 overlay·page error가 없고 주요 조작 요소가 표시되는지 확인
