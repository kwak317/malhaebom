# 준비 대화 API·DB 실행 연결

## 목적과 변경
후보 schema/정책을 인증된 준비·1차 코칭 API와 연결했다. 대화/초안/동의/확인 경력은 24시간 상태이며 service_role만 쓴다. 사용자 소유·만료·요청 ID·DB version CAS·세션 재결합 금지를 검증한다. 저장 후보 전체의 값과 원문을 서버가 표시한 뒤 명시적 동의로 저장한다. 실제 DB 실패 시 완료 응답을 반환하지 않는다.

같은 연습의 확인된 추가 경력은 코칭/비교 후 대화에 reference_only로 전달한다. 원래 revision·기존 점수·판정은 수정하지 않는다. 단계 이동/건너뛰기는 지원하지 않으며 재답변은 UI가 응답을 받은 뒤 열도록 요청한다. 메인 코칭 Prompt/Skill/model은 유지한다.

## 검증
Docker에서 정책/JSON 복구/runtime/API/참고자료/코칭/면접 대화 관련 82 tests 통과. API 401·상태 주입 422, 저장 실패/중복/경합, 타인 대화와 세션 재연결 거절 확인. 원본 자료 누락으로 초기 실행이 실패했고 configs/skills/prompts를 포함한 환경에서 재검사했다. read-only 추가 검토에서 숨은 facts 동의 문제를 찾아 서버 요약으로 해결했다.

## 의존성과 한계
정책 PR #194를 base로 한다. 그 base의 지원자료 전달 변경은 #178에서 기존 이력서 브랜치에 머지됐으나 main 반영은 별도다. UI #191, Prompt/Skill #192, 평가 #193이 같은 릴리스 의존성이다. DB migration → backend → frontend 순서로 배포한다. PREPARATION_CONVERSATION_ENABLED=false 기본값이며 운영에서 승인된 릴리스에만 켠다. 아직 실제 사용자 마이크·STT 전체 E2E의 증거가 아니다. 운영 검증은 배포 후 별도 기록한다.
