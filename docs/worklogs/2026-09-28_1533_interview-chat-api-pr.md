# Worklog — 면접 대화 API 연결

- 변경: 기존 main의 MCP lifespan·health 및 /api/agent의 코칭 관측·비용 제한을 보존하고 `/api/agent/chat`만 연결한다.
- 인증 누락, 소유자·만료·기록 변경·비교 전, 중복 요청, 종료 후 입력 및 provider 오류를 API 테스트한다.
- main의 provider 결과 객체는 선행 서비스에서 해석한다. 원래 사용자 DB 기록은 쓰지 않는다.
- API 13개와 프런트엔드 API 계약 3개 통과. 실제 녹음 E2E는 별도다.
- 선행: interview-chat-service. 후속 화면·SDK는 별도 PR. 평가/mock 제출자료와 원격 설정을 제외하고 머지하지 않는다.
- 초기 테스트에서 main에 없던 CreditsError import를 확인해 보완했고 재실행은 모두 통과했다.
