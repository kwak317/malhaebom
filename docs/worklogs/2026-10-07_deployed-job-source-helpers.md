# 운영 공고 소스 helper 동기화

- pinned 운영 이미지에서 개별 공고 URL/원문 검증 helper, 공식 공개 목록 조회, Cloud PlayMCP token store 코드를 반영한다.
- 추천 서비스 연결은 다음 PR에 분리했다. source parser/catalog/token store 단위 테스트만 이 PR에 포함하며 전체 integration 테스트는 연결 PR에서 복원한다.
- URL host/ID·신입/마감 검증, 공개 목록 구조 검증, 공유 auth object 경쟁 갱신을 포함한 18 tests 통과.
- 운영 객체/설정/DB/배포에 쓰기 작업 없음.
