# 운영 실행 소스와 main 동기화

## Why
현재 운영에 이력서·채팅·탐색 변경이 있으나 main과 다르다. 소개페이지 배포로 운영 기능이 사라지는 것을 방지한다.

## Goal
운영 프런트엔드 181파일의 SHA1과 JS/CSS 재빌드를 확인한 원본을 기준으로 실행 소스를 main에 반영한다. 사용자가 백엔드도 운영 실행 코드 기준 통합을 승인했다. 기존 main 평가·개발 자료를 보존한다.

## What
운영 기능 보존 후 소개 → 필요한 로그인 → 채팅, 서비스 홈 유지. 새 URL 경로와 운영 내부 방문 기록을 정합화한다. 운영에 없는 main 전용 파일을 일괄 삭제하지 않는다.

## How
프런트 기준 dpl_JAwKCE3zfgof5TDxe2A6GevT3AxQ, 원본 181파일 UID=SHA1 일치 및 재빌드 JS/CSS 동일. 백엔드는 현재 traffic/image 확인 후 immutable 이미지 원본과 main 비교. credentials/환경값/개인정보는 커밋하지 않는다. 책임별 PR core <=800.

## AC
- Given 운영 기준 When 동기화 Then 기존 이력서/PDF/채팅 기능 파일이 보존된다.
- Given 소개화면 When 연습 시작 Then 세션 확인 후 로그인 또는 채팅으로 간다.
- Given 앱 페이지 이동 When 앱/브라우저 뒤로가기 Then URL·화면·forward 방문이 일치한다.
- Given main 평가자료 When 운영 이미지에 없음 Then 자동 삭제하지 않는다.
- Given 검증된 main When 배포 Then 공개 도메인 assets가 빌드 결과와 일치한다.
