# 저장소 문서와 자산 탐색 정리

## Why
README의 배포/기본 Prompt 설명이 오래됐고 최신 안내와 과거 기록·평가 후보를 구분하기 어렵다.

## Goal
README → 문서 인덱스 → 평가 안내 → 미사용 자산 순서로 정리한다. 실행 폴더·평가 원본·기존 작업을 보존한다. 제외: 앱 동작·운영 배포·Prompt/Skill 변경. 후속 사용자 스크린샷의 재현성 조건을 README 및 예제 환경값에 적용한다.

## What
최신 주소·기능·기준을 README에 안내한다. 기존 문서 경로를 유지하고 Worklog 전체 인덱스로 이력을 찾게 한다. 평가 운영 기준/후보/과거 결과를 구분한다. 미참조 public demo WebP 4개를 원본 그대로 보관한다.

## How
main e6ecc4b 기준의 별도 브랜치. 사용 중인 PNG/demoRouter는 유지한다. 정리 전에 Git 상태를 확인했고 기존 frontend/.gitignore는 보존한다. 파일 이동은 SHA256 및 코드/HTML/CSS 참조 검사로 확인한다.

## AC
- Given 처음 방문 When README Then 주소·기능·실행·제출 자료를 찾는다.
- Given 과거 결과 When 문서/평가 인덱스 Then 현 운영 증거로 혼동하지 않는다.
- Given archive When SHA256 비교 Then 원본 동일하며 링크/빌드가 통과한다.
- Given runtime When diff Then 운영 실행 코드·평가 원본의 변경이 없다. 예제 환경값 변경은 명시된 두 항목에 한정한다.

- Given 새 clone When 예제 환경값으로 Compose 기동 Then 기동 시간과 웹/API/healthy 결과를 기록하며, 실제 provider/로그인/음성 재현 조건은 별도로 명시한다.

사용자 후속 요청의 로컬 전용 실행 이미지 변경은 [CPU 재현 Spec](local-cpu-reproduction.md)으로 구분한다. 운영 배포는 변경하지 않는다.
