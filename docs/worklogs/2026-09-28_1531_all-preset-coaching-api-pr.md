# Worklog — 기본 질문 10개 API·MCP 연결

- 목적: 기존 화면 질문 1~10번의 서버 카탈로그와 코칭 허용 범위를 연결한다.
- 변경: coaching_questions, coaching_runtime, Supabase 문맥, Skill 버전 메타데이터, 기록의 기준 이름, 환경 예시와 범위 문서.
- 검증: 질문 카탈로그·실제 stdio MCP·합성 REST의 10문항 연결/질문 불일치 차단 테스트와 전체 backend 회귀 테스트를 실행한다.
- 격리 backend 446개, 카탈로그/MCP 연결 3개 통과. 화면 기준 이름도 질문별로 표시한다. 실제 모델/사용자 DB·녹음 완주 품질 평가는 별도다.
- main의 6개 문제 해결 기준·비용 제한·재시도·관측·HTTP MCP는 보존한다.
- 선행 PR: preset-coaching-skill-catalog. 후속 면접 대화·SDK는 별도 PR이다.
- 제외: evals, 제출용 mock/프롬프트 자료, 기존 다른 변경. 머지는 하지 않는다.
