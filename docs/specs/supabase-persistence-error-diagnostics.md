# Supabase 저장소 오류 진단 Spec

## Why

- **페르소나**: 로컬에서 면접 답변 분석을 실행하는 개발자와 발표 담당자
- **상황**: 분석 요청 시 Supabase Storage 또는 Database가 거절할 수 있다.
- **문제**: 기존 오류는 모든 실패를 같은 문구로 보여, 버킷·RLS·키 설정 문제를 구별할 수 없다.
- **측정 지표**: 저장소 요청 실패 시 HTTP 상태 코드 확인 가능률 100%

## Goal

- **해결 목표**: 저장소 요청 실패 화면에 HTTP 상태 코드와 안전한 범주의 안내를 표시한다.
- **성공 기준**: 401·403·404·그 외 HTTP 오류가 각각 구분되어 표시되고, 테스트로 확인한다.
- **Out of Scope**: Supabase 응답 원문, JWT·API 키·파일 경로·사용자 음성의 표시 또는 로그 기록

## What

**Happy Path**
1. Storage/REST 요청이 성공하면 기존 동작을 유지한다.
2. 요청이 실패하면 상태 코드에 맞는 안전한 한국어 안내를 API 오류 응답에 포함한다.

**Edge Cases**

| 상황 | 처리 방식 |
| --- | --- |
| 401 | 인증 설정 확인 안내와 `HTTP 401` 표시 |
| 403 | Storage RLS 정책 확인 안내와 `HTTP 403` 표시 |
| 404 | 버킷 또는 테이블 확인 안내와 `HTTP 404` 표시 |
| 기타 상태 | 일반 실패 안내와 해당 HTTP 상태 표시 |
| 네트워크 오류 | 기존 연결 불가 안내 유지 |

## How

- 대상: `backend/app/services/supabase_persistence.py`
- 실패 응답의 `status_code`만 사용한다.
- 응답 본문, Authorization 헤더, API 키, 객체 경로는 API 응답과 로그에 포함하지 않는다.
- 기존 `SupabasePersistenceError` 계약과 FastAPI의 422 응답 형식을 유지한다.

## AC (Given-When-Then)

- GIVEN: Storage 요청이 403을 반환한다. WHEN: 분석 작업을 생성한다. THEN: `HTTP 403`과 RLS 정책 확인 안내가 포함된 `SupabasePersistenceError`가 발생한다.
- GIVEN: 저장소 요청이 404를 반환한다. WHEN: 요청한다. THEN: `HTTP 404`와 버킷 또는 테이블 확인 안내가 포함된다.
- GIVEN: 저장소 요청이 성공한다. WHEN: 분석 작업을 생성한다. THEN: 기존 업로드·행 생성 흐름이 유지된다.
