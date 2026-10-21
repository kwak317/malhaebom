# 운영 NCS DB 재시도 소스 동기화

- 운영 pinned backend의 NCS API 최초 시도/명시적 DB 재시도 분기와 저장소를 가져왔다.
- 첫 조회는 공식 API만 사용한다. source=database 재시도는 마지막 검증된 DB snapshot을 조회하고 외부 API를 호출하지 않는다.
- 기존 운영 마이그레이션 두 파일을 같은 이름/내용으로 저장한다. RLS 및 service_role 전용 최소 SELECT/INSERT/UPDATE grants 확인. DB에 실행하지 않았다.
- NCS 13 tests 통과. REST 저장/조회 및 인증 분기는 mock으로 검증했다. 운영 DB 변경/실사용자 E2E는 수행하지 않았다.
