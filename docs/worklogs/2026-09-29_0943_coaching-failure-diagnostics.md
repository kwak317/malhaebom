# Worklog — 코칭 실패 지점 기록

- 일시: 2026-09-29 09:43 KST
- 작업자: Codex
- 관련 이슈/PR: 생성하지 않음
- 요청: 실패 지점마다 어디서 무엇이 실패했는지 기록

## 1. 목적

코칭의 실패 단계·오류 코드·모델 호출 횟수·시도별 실패 이력을 기록한다.

## 2. 작업 전 상태

Langfuse에는 최종 HTTP 상태 기반 `failure_state`와 지연·버전 등이 기록됐다. 파싱과 검증 실패, 보정 이력은 구분되지 않았다. 기존 관련 테스트 26개가 통과했다. 작업 시작 전 여러 기존 수정·미추적 파일을 확인하고 보존했다.

## 3. 수행 내용 및 판단

- 요청별 ContextVar의 진단 객체를 worker thread와 공유해 동시 요청의 이력을 분리했다.
- 문맥·provider·parse·validation·persistence 단계와 고정 오류 코드를 기록한다. 호출 전 실패는 시도 0회다.
- 성공한 보정도 이전 실패 이력을 유지한다. 파싱 오류는 자동 재시도하지 않고 검증 오류는 기존 최대 1회 보정을 유지한다.
- 원문·토큰·예외 메시지를 새 로그에 넣지 않는다. 로컬 이벤트와 Langfuse metadata는 동일 trace ID를 사용한다.
- 관측 전송 장애는 로컬 고정 코드만 기록하고 사용자 응답에 영향을 주지 않는다.

## 4. 변경 파일

- `backend/app/services/coaching_diagnostics.py`: 요청별 진단·실패 이벤트
- `backend/app/services/coaching_runtime.py`: 단계별 기록과 시도 집계
- `backend/app/services/coaching_observability.py`: 진단 metadata 필드
- `backend/app/main.py`: 요청 scope·trace 연결·관측 장애 로그
- `backend/tests/test_coaching_diagnostics.py`: 실패/보정/동시 요청/민감값 보호 검증
- `docs/specs/coaching-failure-diagnostics.md`, `docs/CURRENT_STATE.md`, `docs/ARCHITECTURE.md`, 본 Worklog

## 5. 검증

기존 API 이미지의 별도 `docker run --rm --network none`에서 저장소를 `/workspace:ro`로 연결했다. 실제 provider·Langfuse를 호출하지 않았다.

```text
python -B -m unittest tests.test_coaching_diagnostics tests.test_coaching_runtime
  tests.test_coaching_api tests.test_coaching_observability tests.test_coaching_validation
  tests.test_preset_coaching tests.test_interview_chat tests.test_github_readme_analysis
  tests.test_job_search_intent
81 tests OK
```

확장 테스트의 첫 실행은 기존 `test_preset_coaching.py`가 top-level `test_coaching_api`를 import해 실패했다. 테스트 실행 환경의 `PYTHONPATH=/workspace/backend/tests:/workspace/backend:/workspace`를 설정해 해결했다. 테스트 소스는 수정하지 않았다. 좁은 검증은 앞서 43개가 통과했다.

## 6. 발견한 문제 / 미확인 사항

- 전체 `git diff --check`는 기존 `.github/PULL_REQUEST_TEMPLATE.md`의 두 trailing whitespace 때문에 실패했다. 해당 파일은 수정하지 않았다.
- 운영 API 재빌드·재시작, 실제 모델 장애 유도 및 실제 Langfuse 수신 확인은 수행하지 않았다. 변경은 소스와 격리 테스트에서 검증됐다.

## 7. 다음 작업

운영 반영 후 승인된 검증 데이터로 실제 실패 trace의 진단 metadata 수신을 확인한다.

## 8. 후속 제출 문서 반영

- 사용자 요청에 따라 상위 `말해봄_D6_실제LLM_검증재시도_20260929.md`에 5번 에러 로깅 항목을 추가했다. 서버 로그·Langfuse metadata의 기록 항목, 형식 예시, 보정 후 실패 이력 보존, 민감값 제외, 관측 장애 처리와 운영 미확인 범위를 설명한다.
- 원문을 `output/doc-backups/말해봄_D6_실제LLM_검증재시도_20260929.before-error-logging-094744.md`로 백업했다. 기존 본문을 보존하고 에러 로깅 항목만 추가했다.
- 소스 및 기존 테스트 기록과 설명을 대조하고 Markdown fence, 로그 예시 JSON, 코드 링크, 추가 전후 diff를 확인했다. 문서만 변경했으며 API 코드·설정·운영 서비스는 수정하지 않았다. 새 모델 호출·Langfuse 전송·운영 실패 유도·테스트 재실행은 수행하지 않았다.
