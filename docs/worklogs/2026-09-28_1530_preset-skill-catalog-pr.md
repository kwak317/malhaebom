# Worklog — 기본 면접 질문 Skill 카탈로그

- 기준: origin/main c5b4f91, 별도 PR 준비 checkout.
- 목적: 기본 질문 확장에 필요한 Skill 기준과 유형별 버전 검증을 먼저 추가한다.
- 변경: criteria.json, SKILL.md, preset-interview.md, coaching_skill.py와 테스트, 기능 Spec.
- 기존 문제 해결 6개 기준과 problem-solving-v4-draft.3을 보존한다. API의 질문 허용 범위 연결은 후속 PR이다.
- 검증: Docker 격리 test_coaching_skill.py 4개 통과. diff 및 PR 크기 확인.
- 기존 로컬 checkout·서버·평가셋·제출용 mock/프롬프트 자료는 변경하지 않는다.
- SDK/질문 확장/면접 대화 작업을 최신 main과 통합하는 과정이며 실제 사용자 E2E는 별도다.
- 머지하지 않고 리뷰용 PR로 남긴다.
