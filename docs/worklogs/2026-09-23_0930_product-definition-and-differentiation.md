# 2026-09-23 제품 문제정의·차별화 전략 문서화

## 목적

말해봄의 현재 MVP 문제 정의와 제품 차별화 방향을 저장소에서 함께 추적할 수 있도록 문서화한다.

## 작업 전 상태

- `docs/PROJECT_OVERVIEW.md` 등에는 현재 MVP 방향과 제약이 정리되어 있었지만 별도 문제정의서 문서는 없었다.
- 차별화 가설은 프로젝트 제안서 일부에 존재했으나 경쟁 서비스 비교와 발표용 포지셔닝을 한 문서에서 관리하지 않았다.

## 수행한 작업

- `docs/product/problem-definition.md`를 추가했다.
- `docs/product/differentiation-strategy.md`를 추가했다.
- 문제정의서의 판정 상태와 활성 기준 표현을 실제 Skill·런타임 계약에 맞췄다.
- `docs/README.md`에 두 문서의 역할과 canonical 문서와의 관계를 연결했다.

## 주요 판단과 이유

- 문제정의서는 사용자 문제·검증 가설을 설명하는 제품 문서로 두고, 현재 구현·목표 범위·구현 계약의 기존 canonical 문서를 대체하지 않는다.
- 두 문서는 목적이 달라 합치지 않고 `docs/product/` 아래에서 각각 관리한다.

## 변경 파일

- `docs/product/problem-definition.md`
- `docs/product/differentiation-strategy.md`
- `docs/README.md`
- `docs/worklogs/2026-09-23_0930_product-definition-and-differentiation.md`

## 검증 내용

- 저장소 필수 문서와 현재 MVP 제약을 대조했다.
- `TARGET_STATE.md`, `prd.md`, `skills/SKILL.md`의 활성 기준·4상태 계약과 문제정의서 표현을 대조했다.
- 코드 변경이 없는 문서 전용 작업이므로 런타임 테스트 대상은 없다. PR 단계에서 diff와 저장소 정책 검사를 확인한다.

## 발견한 문제

- 문제정의서가 `undetermined`를 누락하고 C/R/A/D/V 전체를 일괄 평가하는 것처럼 읽힐 수 있었다.

## 미확인 사항

- 경쟁사 공개 페이지의 기능은 2026-09-22 조사 시점 기준이며 이후 변경될 수 있다.

## 다음 작업

- 발표/README에서 제품 설명을 사용할 때 두 문서의 표현을 기준으로 정렬한다.

> 2026-10-04 사용자 요청으로 도메인 확장을 범위 밖으로 두는 문구를 삭제했다. 당시 수행·검증 기록은 현재 기능의 완료 증거로 확대하지 않는다.
