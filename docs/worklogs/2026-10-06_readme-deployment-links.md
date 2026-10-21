# Worklog — README 배포 주소 추가

- 일시: 2026-10-06
- 작업자/에이전트: Codex
- 관련 요구사항/결정: 사용자 요청 “read.me 에 배포주소 넣어줘”

## 1. 목적
README에서 공개 서비스와 Backend API에 바로 접근할 수 있게 한다.

## 2. 작업 전 상태
최신 main `6aa668e`에는 README 배포 주소가 없고 배포 URL을 확인 필요 항목으로 기술했다. 기존 배포 기록의 서비스 도메인과 Cloud Run 실조회 주소를 확인했다.

## 3. 수행 내용
README 상단에 서비스·Backend·health 링크, 확인 날짜와 운영 revision을 추가하고 하단의 배포 URL 확인 필요 문구를 갱신했다.

## 주요 판단과 이유
현재 공개 주소와 HTTP 응답만 기록한다. 접속 성공을 로그인 E2E·LLM 품질 검증으로 확대하지 않는다. 과거 중지 당시 기록은 수정하지 않는다.

## 4. 변경 파일
- `README.md`: 배포 링크와 접속 상태.
- 이 Worklog 및 `docs/worklogs/README.md`: 변경 기록.

## 5. 검증
- `https://malhaebom.xyz`: HTTP 200, `content-type: text/html`.
- Cloud Run `status.url`: `https://malhaebom-mk2-fmf5h3xp4q-du.a.run.app`.
- 위 API `/health`: HTTP 200, `{"status":"ok"}`.
- `gcloud run services describe`: `malhaebom-mk2-resume-1004-1438`에 트래픽 100%.
- README의 링크·문서 차이 및 `git diff --check` 확인.

## 6. 발견한 문제 / 남은 리스크
접속 상태는 확인 시점의 결과다.

## 미확인 사항
로그인 사용자 E2E와 모델 품질은 이번 작업에서 검증하지 않았다. 코드·배포·운영 설정 변경 없음.

## 7. 다음 작업
PR 리뷰 후 병합한다.
