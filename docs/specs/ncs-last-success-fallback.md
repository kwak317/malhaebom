# NCS 마지막 정상 조회 결과 fallback

## Why
NCS API 지연으로 첫 자기점검 단계가 HTTP 503에 막힌다.

## Goal
실시간 우선 조회를 유지하고 실패 시 해당 서버 프로세스의 마지막 검증된 정상 결과로 연습을 이어간다. 캐시 출처와 조회시각을 화면에 표시한다.

## What
정상 조회 → 검증된 9항목과 조회시각 저장. 후속 timeout/HTTP 오류/응답 형식 또는 능력단위 검증 실패 → 마지막 정상 목록 반환. 복구 → 새 정상 목록으로 교체. 정상 기록이 없거나 키가 없으면 기존 503/다시 시도 유지.

## How
서버 프로세스의 공유 NCS 서비스에 lock으로 보호한 메모리 snapshot을 둔다. 사용자별 데이터/키/원문을 캐시에 넣지 않고 공개 NCS 목록만 보관한다. 응답 data_source(live/cached), fetched_at(UTC)을 추가하며 이전 클라이언트와 응답은 호환한다. 화면은 cached일 때 마지막 조회시각과 실시간 실패를 표시한다. 예외 로그에는 오류 클래스·cache 사용 여부만 남긴다. 서버 재시작·새 인스턴스는 빈 캐시이며 영구 저장·DB migration·정적 목록 대체·배포는 범위 밖이다.

## AC
- Given 정상 조회 이력 When timeout/비정상 응답 Then 동일 목록과 원래 조회시각을 cached로 반환한다.
- Given 정상 이력 없음 When 실패 Then 기존 오류가 발생한다.
- Given 실패 이후 API 복구 When 조회 Then live와 새 조회시각으로 돌아온다.
- Given 반환 객체가 변경됨 When 다음 fallback Then 보관 snapshot은 변하지 않는다.
- Given cached 응답 When 화면 표시 Then 이전 조회 목록 안내와 선택·다음 단계 진행이 가능하다.
