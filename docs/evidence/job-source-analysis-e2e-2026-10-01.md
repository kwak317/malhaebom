# 배포 환경 공고 원문 분석 API 흐름 증거 — 2026-10-01

## 범위

배포된 Cloud Run 서비스의 공고 추천 → 선택 공고 분석 → 연습 세션 생성 요청 성공 기록을 정리했다. 2026-10-06에 기존 보존 로그를 문서화했으며, 새 운영 E2E를 실행한 결과가 아니다.

관측 경로:

`README 분석 200 → 공고 추천 200 → 선택 공고 원문 분석 endpoint 201 → 연습 세션 생성 201`

기존 이 파일에 있던 로컬 인증 API E2E는 [로컬 실행 원본](job-source-analysis-local-e2e-2026-10-01.md)에 내용 변경 없이 보존했다. 로컬 요구사항 5건·인용 검증·저장/조회 결과는 아래 운영 결과에 합치지 않는다.

JWT, 사용자 ID, 공고 전체 URL·원문, 요구사항 인용, 저장 UUID, 응답 본문은 운영 증거에 포함하지 않는다.

## 최종 실행 환경

- 실행 날짜·시각: 2026-10-01 22:56~22:57 KST
- 환경: GCP Cloud Run 배포 서비스
- GCP project: `malhaebom-mk2-20261001`
- 서비스: `malhaebom-mk2`
- 실행 revision: `malhaebom-mk2-ncs-recheck-2248`
- 증거 출처: 당시 Google Cloud Logging read-only export로 보존한 request log
- 인증 사용자·NCS 선택·검색 provider·공고 출처: 이 보존 로그에는 값이 없어 미확인
- 문서 정리일: 2026-10-06

위 revision은 당시 실행 환경이다. 이번 정리에서 확인한 현재 운영 revision `malhaebom-mk2-resume-1004-1438`의 테스트 결과로 바꾸지 않는다.

## 최종 redacted 결과

| 시각(KST) | API | 결과 | 확인 범위 |
| --- | --- | --- | --- |
| 22:56:21.764803 | `POST /api/github/readme/analyze` | 200 | README 분석 요청 정상 응답 |
| 22:56:28.757117 | `POST /api/job-search/recommendations` | 200 | 공고 추천 요청 정상 응답 |
| 22:56:50.968453 | `POST /api/job-search/recommendations/analyze` | 201 | 선택 공고 분석 endpoint 성공 응답 |
| 22:57:25.608985 | `POST /api/practice-sessions` | 201 | 연습 세션 생성 성공 응답 |

4건 모두 `malhaebom-mk2-ncs-recheck-2248`의 기록이다. [Redacted 운영 로그 JSON](job-source-analysis/2026-10-01/production-request-events.redacted.json)에 정확한 UTC·KST 시각, revision, HTTP method/path/status와 원본 SHA256을 보존했다.

## 판정

- 로컬 이외에 **배포 환경의 공고 추천·원문 분석·연습 세션 생성 성공 응답 기록도 존재**한다.
- 서버의 시간순 요청 성공 기록으로 API 흐름의 운영 응답을 확인했다.
- 공통 사용자·공고·세션 ID 또는 trace 연결이 없어, 4건을 동일 사용자의 단일 E2E라고 확정하지 않는다.
- 운영 요구사항 수·원문 quote gate·저장 레코드 조회·선택 요구사항 수는 이 로그만으로 확인하지 못한다.
- 새 LLM 분석인지 기존 저장 공고 재사용인지도 구분되지 않는다. 201을 새 추출 결과 검증으로 확대하지 않는다.

따라서 이 문서는 **과거 배포 환경의 API 요청 성공 증거**다. 원문 인용·저장 상세까지 확인한 현재 버전의 브라우저 E2E 완료 증거는 아니다.

## 실행 중 관찰한 실패와 복구

수록된 운영 4건에는 실패나 복구 로그가 없다. 로컬 원본의 NCS 503·PlayMCP 503·JWT 401 및 복구 기록은 다른 실행이므로 운영의 실패·복구 결과로 기재하지 않는다.

## 제한

- 운영 응답 본문과 브라우저 결과 화면은 보존 로그에 포함돼 있지 않다.
- 서버 로그의 시간 순서와 revision 일치가 요청 간 동일 사용자·공고 연결을 보장하지 않는다.
- API 200/201은 해당 요청의 성공 응답 근거이며, 요구사항 의미 품질·LLM 신규 호출·원문 인용·DB 저장 내용까지 보장하지 않는다.
- 현재 운영 revision의 새 E2E는 이번에 실행하지 않았다.
- 근거 JSON은 저장소 밖 `output/coaching-e2e-evidence-20261002/production-api-log.redacted.json`의 events 중 위 4개 endpoint만 추출한 것이다. 원본 해시는 JSON에 기록했으며 이번에 로그를 새로 생성하지 않았다.
