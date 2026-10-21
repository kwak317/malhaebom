# 2026-10-06 NCS 실시간 우선·마지막 정상 목록 fallback (로컬)

## 요청과 범위
사용자가 실시간 NCS 조회 실패 시 마지막 정상 조회 목록으로 진행하고 이전 조회임을 안내하는 방식을 승인했다. 운영 배포는 별도 미승인/미수행이다.

## 변경
NcsCompetencyService의 정상 9항목 검증 이후 UTC 조회시각과 목록을 lock으로 보호한 메모리 snapshot으로 보관한다. 다음 조회는 항상 외부 API부터 호출하고 timeout/HTTP/응답 계약/능력단위 검증 실패 시 snapshot을 깊은 복사해 data_source=cached로 반환한다. 정상 응답은 live이고 복구 시 snapshot이 갱신된다. 실패 데이터와 caller mutation은 캐시를 덮어쓰지 않는다. 캐시에 키·사용자 자료는 없다. 경고 로그에는 오류 클래스와 캐시 여부만 남긴다.

화면에 마지막 정상 조회 목록 사용 안내와 한국 시각을 표시하며 기존 선택·이력서 단계로 진행한다. 이전 응답/클라이언트의 필드 호환을 유지한다. 정상 기록이 없거나 키가 없으면 기존 오류/다시 시도를 유지한다.

## 파일
backend/app/schemas/ncs_competency.py, backend/app/services/ncs_competency.py, backend/tests/test_ncs_competency.py, frontend/src/api/practiceSetup.ts, frontend/src/pages/PracticePage.tsx, frontend/src/pages/PracticeSetupFlow.test.tsx, docs/specs/ncs-last-success-fallback.md. 작업 직전 백업과 이번 증분은 output/ncs-fallback-20261006/before 및 change.patch. 앞서 applicant_context 변경을 보존하며 이번 patch는 그 위의 NCS 변경만 담는다.

## 검증
- backend NCS 10 tests PASS: 정상 조회→timeout→fallback→복구, 형식/능력단위 오류, 키 미노출, 객체 변조 격리, cold cache 실패, 인증 API 200 cached/401 유지.
- frontend API/설정 흐름 32 tests PASS: 이전 조회 안내/시각/선택 뒤 다음 단계 진행 포함. jsdom 렌더 검증이며 실제 로그인 브라우저 E2E는 아니다.
- 원본 node_modules의 기존 중복 타입 폴더를 건드리지 않고 앞서 준비한 깨끗한 frontend-build 의존성 환경에서 최신 source를 동기화해 tsc/Vite production build PASS.
- git diff --check PASS.

## 제한·미확인
프로세스 메모리 캐시이므로 서버 재시작·새 인스턴스에는 정상 조회가 한 번 필요하다. 현재 장애가 첫 요청부터 지속되면 이 버전만 배포해도 즉시 목록을 복구할 수 없다. 이전 성공 목록을 소급 생성하거나 검증되지 않은 정적 목록을 정상 조회로 표시하지 않는다. 캐시가 있어도 실패한 실시간 요청의 기존 최대 10초 대기는 남는다. 영구 캐시·DB 변경·재시도 정책·운영 배포는 수행하지 않았다. 실제 공공 API 장애/복구 및 운영 사용자 흐름은 미검증이다.
