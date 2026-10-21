# 운영 작업 히스토리·근거 자료실 component 동기화

- 운영 source의 작업/메시지/근거 ID 연결, 자료실 카드, 답변 근거 지도와 코칭 결과 연결 component를 반영한다.
- 확정 전사문과 실제 인용 연결만 표시하며 원문 불일치/없는 문장/비활성 기준을 연결하지 않는다.
- component 22 tests 및 production build 통과. 원문 선택·focus·revision 분리·근거 불일치 확인.
- 새 결과 도착 시 과거 읽기 위치 보존 integration 기대값은 기존 auto-scroll hook과 다른 운영 hook을 필요로 하므로 다음 스크롤 PR에서 복원/검증한다.
- PracticePage sidebar 연결은 다음 PR. 배포/DB/운영 설정 변경 없음.
