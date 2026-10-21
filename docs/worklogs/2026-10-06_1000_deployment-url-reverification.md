# Worklog — 공개 배포 주소 재검증과 체크포인트 정합성

- 일시: 2026-10-06 10:00 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: D10 배포 URL, 최종 제출 URL

## 1. 목적

Checkpoint 조별 현황에서 3조의 배포 URL이 미충족으로 표시된 상태와 최신 저장소를 대조하고, 공개 주소를 직접 재검증해 저장소의 체크포인트 상태를 실제 증거와 일치시킨다.

## 2. 작업 전 상태

- 최신 `origin/main`의 README에는 Frontend, Cloud Run API, `/health` 주소와 2026-10-06 확인 결과가 이미 기록돼 있었다.
- 체크포인트 작업표의 세부 D10 배포 URL 항목은 완료였지만 상단 진행상황 요약은 배포 `[ ]`, D10 미완료로 남아 있었다.
- 외부 접속과 CORS를 이번 작업에서 새로 재검증하기 전이었다.

## 3. 수행 내용

- Frontend에 외부 GET을 보내 HTTP 200을 확인했다.
- Cloud Run `/health`에 GET을 보내 HTTP 200과 `{"status":"ok"}` 응답을 확인했다.
- Frontend Origin과 `Authorization` 요청 헤더를 사용한 API CORS preflight에서 HTTP 200과 허용 Origin·메서드·헤더를 확인했다.
- 체크포인트 상단 배포 상태를 `[x]`로 맞추고, D10은 공개 URL 완료와 production trace/Prompt rollback 미완료를 구분해 `일부 완료`로 기록했다.

## 주요 판단과 이유

- 공개 주소 접속과 CORS는 직접 재현했으므로 배포 URL 항목은 완료로 표시한다.
- 로그인 사용자 전체 E2E, 코칭 품질, production Langfuse trace, managed Prompt rollback은 이번 읽기 전용 검증 범위가 아니므로 D10 전체를 완료로 표시하지 않는다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `docs/CURRENT_STATE.md` | 공개 배포 주소와 CORS 재검증 결과 추가 |
| `docs/project2-checkpoint-work-cards.md` | 상단 배포·D10·최종 제출 상태 정합성 수정 |
| `docs/worklogs/2026-10-06_1000_deployment-url-reverification.md` | 실행 명령과 결과, 미확인 범위 기록 |
| `docs/worklogs/README.md` | Worklog 인덱스 추가 |

## 5. 검증

```text
curl.exe -sS -D - -o NUL https://malhaebom.xyz/
HTTP/1.1 200 OK (Server: Vercel)

curl.exe -sS -D - https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app/health
HTTP/1.1 200 OK
{"status":"ok"}

curl.exe -sS -D - -o NUL -X OPTIONS -H "Origin: https://malhaebom.xyz" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization" https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app/api/job-recommendations
HTTP/1.1 200 OK
access-control-allow-origin: https://malhaebom.xyz
access-control-allow-methods: GET, POST, DELETE
access-control-allow-headers: Accept, Accept-Language, Authorization, Content-Language, Content-Type
```

## 6. 발견한 문제 / 남은 리스크

- Checkpoint 웹페이지의 자동 판정은 최신 README 반영 전 캐시 또는 스캔 시점을 표시할 수 있다.
- 공개 URL 200은 인증 후 전체 사용자 흐름과 동일한 증거가 아니다.

## 미확인 사항

- 현재 리비전의 로그인 사용자 전체 E2E
- 같은 요청의 production Langfuse trace와 Prompt·Skill 버전
- managed Prompt release manifest와 rollback

## 7. 다음 작업

- 배포 smoke 검증의 기존 자동화 여부를 조사하고, 중복되지 않을 때만 별도 테스트 브랜치로 보강한다.
- D11 baseline 사전검증과 제출 증거 인덱스를 각각 별도 브랜치에서 진행한다.
