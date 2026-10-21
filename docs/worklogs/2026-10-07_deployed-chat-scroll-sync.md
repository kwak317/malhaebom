# 운영 채팅 하단 추적·참고자료 API 동기화

- 마지막 운영 프론트 source의 submit/advance 명시적 하단 이벤트, ResizeObserver 지연 말풍선 추적, 수동 과거 탐색 시 추적 해제를 반영한다.
- 확인 후 저장한 경험 조회와 공고 검색 conversation ID 전달, NCS DB 재시도 API를 연결한다. 세 점 로딩 표시도 같은 component로 가져왔다.
- #191 bind 실패 시 녹음 계속 진행 회귀를 보존한다. 이전 PR에서 분리한 과거 읽기 위치 보존 integration 테스트를 복원했다.
- 훅/workspace/준비 대화/API 48 tests 및 production build 통과. 이벤트 listener/observer 정리와 사용자 스크롤 해제 확인.
- PracticePage에서 다음단계/전송 이벤트를 발행하는 연결은 다음 PR. 운영 배포/DB/설정 변경 없음.
