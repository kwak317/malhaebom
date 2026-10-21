# 운영 연습 기록 UI 및 최종 소스 확인

- 중복 상세보기를 채팅 내역 보기로 바꾸고 저장된 준비 자유질문/확정 경험 대화를 표시한다. 상태·결과 보기·삭제 수평 배치와 운영 버튼 모양을 동기화한다.
- 마지막 프론트 운영 dpl_8zZ1foz3ZdYas9Kp6C9ZUfUzyGZC의 /assets/index-0taWoI2a.js SHA256가 출력 source 빌드와 일치함을 먼저 확인했다.
- backend 기준 revision malhaebom-mk2-consent-hint-1007, image sha256:af58819460ea94f97be67062f3caf8fe5653f8e34f91834a621e1bdfcedbc82d.
- 읽기 확인한 운영 selector: PREPARATION_CONVERSATION_ENABLED=true, COACHING_LLM_MODEL=google/gemini-3.5-flash-lite, LANGFUSE_PROMPT_NAME=malhaebom-coaching-v5-reinforced-verification, LANGFUSE_PROMPT_LABEL=production. label은 가변이며 이 기록은 확인 시점 snapshot이다. 비밀키는 기록하지 않았다.
- main의 승인된 Prompt/Skill 안전 경계와 실제 버전 저장 개선은 운영 이미지의 과거 구현으로 되돌리지 않았다. 기능 소스를 동기화한 것이며 바이너리/기본 Skill이 완전히 같은 복제본이라고 주장하지 않는다.
- 프론트 전체 176 tests 및 production build 통과. 운영 로그인/LLM/DB E2E는 수행하지 않았다.
- 운영 Vercel Git 연결 없음, GitHub workflow는 tests/policy/secret 검사만 있음, Cloud Build triggers 없음 확인. 운영 배포/트래픽/설정/DB는 변경하지 않았다.
