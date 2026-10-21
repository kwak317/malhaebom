# Worklog — Prompt 입력·보안 경계 정적 점검

- 일시: 2026-10-06
- 범위: E2E 제외. 저장소 코드와 Prompt 템플릿만 정적 점검.

## 목적

프롬프트 설계 체크리스트 중 다음 두 항목을 저장소 기준으로 점검한다.

1. 사용자 입력 템플릿과 보안 규칙의 충돌 여부
2. 호출별 system Prompt의 역할·입력·출력·안전 경계 분리 상태

## 수행

- coaching / README 분석 / 공고 분석 / 면접 대화 / 질문별 rubric / 채용 검색 의도 / web-search 질의 경로를 확인했다.
- 대부분의 자유 입력·외부 문서 경로에는 입력을 분석 데이터로 취급하고 내부 지시를 실행하지 않는 경계가 이미 있었다.
- `JobSearchIntentService`만 사용자 메시지를 직접 넣으면서 system Prompt에 명시적인 데이터/지시 경계가 없었다.
- 해당 경로에 데이터 경계를 추가하고 user Prompt를 시작/끝 구획으로 감쌌다.
- 공격 문자열이 system Prompt로 섞이지 않는지 회귀 테스트를 추가했다.
- 전체 정적 점검 결과는 `docs/evidence/prompt-input-security-audit-2026-10-06.md`에 기록했다.

## 판단

- **사용자 입력 템플릿과 보안 규칙의 충돌 점검:** 정적 범위 완료.
- **호출별 system Prompt 역할 단위 섹션 분리:** 부분완료 유지. 모든 호출이 공통 versioned template/section 구조를 쓰는 것은 아니다.
- 신규 인젝션 3건의 provider before/after 실측은 이번 작업 범위가 아니다.

## 변경 파일

- `backend/app/services/job_search_intent.py`
- `backend/tests/test_job_search_intent.py`
- `docs/evidence/prompt-input-security-audit-2026-10-06.md`
- `docs/worklogs/README.md`
- 이 Worklog

## 검증

- `backend/tests/test_job_search_intent.py` 실행
- `git diff --check`

## 승인 PR 병합 충돌 해결 (2026-10-06)

- 최신 main을 병합하며 Worklog 인덱스의 동시 추가 충돌을 해결했다. 양쪽 문서 링크를 모두 보존했다.
- 검증: `git diff --check` 통과. Python 3.12 경량 CI 환경에서 `STT_WARMUP_ENABLED=false python -m pytest backend/tests/test_job_search_intent.py -q`: 7 passed.
- 기존 환경에는 pytest가 없었고 호스트 Python 3.14는 CI 의존성 충돌이 있어 임시 Python 3.12 환경을 사용했다. sandbox TestClient 실행은 정체되어 정상 실행 환경에서 재검증했다.
