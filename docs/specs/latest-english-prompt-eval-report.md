# 최신 영문 Prompt 평가 보고서 갱신

## Why
EVAL_REPORT 4·6·7장에 빈 비교표와 미정 게이트가 남고 측정 Prompt가 현재 기본값과 다르다.

## Goal
동일 합성 v2 30건에서 v4와 최신 v5를 실제 provider로 각각 1회 평가하고, 계약·자동 품질·비용·p50/p95·문항별 회귀와 출시 게이트를 기록한다. 운영 배포·Prompt 원격 게시·Git push는 제외한다.

## What
최신 `coaching-v5-skill-owned`를 평가 대상, 이전 영문 `coaching-user-supplied-v4-verification`을 비교군으로 사용한다. 동일 현재 Skill과 모델을 고정해 Prompt 차이를 비교한다. 과거 다른 Skill의 기록은 별도 역사 자료로 보존한다.

## How
기존 run_model_comparison API와 strict schema/server validator를 사용한다. main의 Gemini 응답 형식도 실측과 같은 strict schema로 맞추고 해당 분기만 테스트한다. 모델 `google/gemini-3.5-flash-lite`, Skill `interview-coach-v6.1-domain-rules`, 각 30건×1회, timeout 45초, max completion tokens 2048, 계약 보정 최대 2호출. 합성 자료만 provider에 보내며 기대 정답은 모델 입력에서 제외한다. 원시 응답은 local-results에 저장하고 본문·Skill·dataset·schema 해시를 보존한다. 최신 후보 측정 전 상태를 기준으로 스키마 ≥95%, p95 ≤10초를 검사하고 비용 상한·사람 안전성/E2E는 미정/미검증으로 남긴다.

## AC
- Given 동일 30건과 Skill, When 두 Prompt 평가, Then 버전·해시·모델 설정·실패/비용을 기록한다.
- Given 결과, When 보고서 갱신, Then 4·6·7장에 실측 비교와 회귀 case, KEEP/DISCARD/보류 근거를 채운다.
- Given 사람 평가 없음, Then 자동 점수를 사람 품질이나 운영 출시 승인으로 표현하지 않는다.
