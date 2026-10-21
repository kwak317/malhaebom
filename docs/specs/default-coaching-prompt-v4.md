# 배포 v4로 코칭 기본 Prompt 복원

## Why
GitHub의 기본값 v5가 운영 이미지의 v4와 다르며, GitHub v4 본문도 배포 원본보다 문장 4줄이 추가되어 있다.

## Goal
환경변수 미설정·공백일 때 배포 v4를 선택하고 v4 템플릿을 배포 원본과 바이트 단위로 맞춘다. Skill·모델 변경, Langfuse 게시, 배포, 병합은 제외한다.

## What
- 기본 선택과 `.env.example`은 `coaching-user-supplied-v4-verification`이다.
- 명시적 v5 선택과 기존 관리형 Prompt 우선·실패 시 로컬 복귀 동작은 유지한다.

## How
- 기본 상수와 설정 예시를 v4로 수정한다.
- 불변 배포 archive의 v4 본문을 사용한다. SHA256: `2d8cf1d83254c65b638d55ec69d10229a7d3e680f274c6ee8e6d02cf65dd0fb1`.
- 현재 GitHub Skill은 보존한다. 이 변경은 배포 Prompt 기본값의 정합성이며 전체 배포 소스 복제가 아니다.

## AC
- Given 버전 미설정 또는 공백, When 로컬 Prompt를 로드, Then v4와 현재 Skill을 결합한다.
- Given v5 명시 설정, When 로드, Then v5 템플릿과 현재 Skill을 결합한다.
- Given 유효하지 않은 관리형 템플릿, When 복귀, Then v4 버전과 본문을 사용한다.
- v4 템플릿 SHA256이 불변 manifest와 일치하고 관련 테스트가 통과한다.
