# Worklog — compare_attempts MCP 구현

- 일시: 2026-09-21 12:51 KST
- 작업자/에이전트: Codex
- 브랜치: `feat/llm-mcp-langfuse-hardening`
- 관련 Spec: `docs/specs/attempt-comparison.md`

## 1. 목적

저장된 1차·2차 코칭 결과를 같은 조건에서만 비교하는 읽기 전용 `compare_attempts` MCP 도구를 구현한다. 추가 LLM 호출 없이 criterion 상태·양쪽 근거·전달력 방향을 계산하고, 사용자·만료·허용 ID 경계를 검증하는 것을 완료 조건으로 둔다.

## 2. 작업 전 상태

- 연습 기록 API 내부에는 결정론적 1차·2차 비교 함수와 프런트 비교 화면이 있었다.
- MCP에는 질문·확정 답변·공고 문맥을 읽는 세 도구만 있었고 코칭 결과 비교 도구는 없었다.
- `answer_revisions`와 `coaching_runs`의 RLS·만료 구조는 존재했으며 새 schema는 필요하지 않았다.

## 3. 수행 내용

1. 기존 연습 기록 비교 함수를 공개 서비스 경계로 재사용하고, `not_observed` 또는 `undetermined`에서 `met`으로 바뀐 경우만 새 설명으로 분류하도록 Spec과 정렬했다.
2. 두 `coaching_runs`와 연결된 revision·analysis job을 읽는 Supabase 저장소와 비교 서비스를 추가했다.
3. 같은 사용자·활성 기간·완료 상태·연습 세션·질문·공고 snapshot·model·Prompt·Skill 버전 및 1차→2차 순서를 검증했다.
4. 비교 전용 scope와 정확한 두 결과 ID에 묶인 최대 5분 capability token을 추가했다. 기존 문맥 조회 토큰과 상호 교환되지 않게 분리했다.
5. FastMCP stdio/HTTP 서버에 `compare_attempts`를 등록하고 Compose E2E fixture를 네 도구로 확장했다.
6. 현재 상태·아키텍처·구현 계획·README를 실제 구현 범위에 맞게 갱신했다.

## 주요 판단과 이유

- 비교는 저장된 구조화 코칭 결과를 서버 규칙으로 계산한다. 세 번째 LLM 호출을 추가하면 결과가 비결정적이고 비용·지연이 늘어나므로 사용하지 않았다.
- Supabase service-role key는 MCP 서버 프로세스에만 두고 브라우저나 응답에 노출하지 않는다. 저장소 쿼리와 서비스 계층에서 사용자·만료를 이중 확인한다.
- 기존 테이블과 RLS로 필요한 데이터를 제한할 수 있어 migration은 추가하지 않았다.
- 원문 전체 transcript는 MCP 응답에서 제외하고 저장된 criterion evidence만 반환한다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/app/services/attempt_comparison.py` | 비교 도메인 서비스·호환성 검사·demo fixture |
| `backend/app/services/supabase_attempt_comparison.py` | 소유자·만료 범위 Supabase 조회 저장소 |
| `backend/app/services/mcp_access.py` | 비교 전용 scope·pair-bound capability token |
| `backend/app/services/practice_history.py` | 비교 함수 재사용 경계와 새 설명 판정 정렬 |
| `mcp_server/server.py` | `compare_attempts` 등록과 의존성 구성 |
| `backend/tests/test_attempt_comparison.py` | 비교·권한·만료·호환성·저장소 query 테스트 |
| `backend/tests/test_mcp_tools.py` | stdio 함수·HTTP transport·scope 분리 테스트 |
| `backend/tests/test_practice_history.py` | Spec에 맞춘 상태 변화 회귀 테스트 |
| `backend/tests/compose_coaching_e2e.py` | Compose 네 번째 MCP 도구 호출 |
| `README.md`, `backend/README.md`, `docs/*` | 현재 도구 수·계약·상태·계획 갱신 |

## 5. 검증

```text
python -m compileall -q backend/app mcp_server backend/tests/compose_coaching_e2e.py
결과: 성공

docker run --rm -v "$PWD:/app" -w /app malhaebom-langfuse-v4-test:latest \
  python -m unittest discover -s backend/tests -p 'test_*.py'
결과: 255 tests, OK

WEB_PORT=18081 API_PORT=18001 docker compose \
  -f docker-compose.yml -f docker-compose.e2e.yml \
  up --build --abort-on-container-exit --exit-code-from coaching-e2e coaching-e2e
결과: screen=ok, api_proxy=ok, mock_contract=needs_more_info,
      mcp_tools에 compare_attempts 포함, exit code 0

git diff --check -- <이번 작업의 추적 파일>
rg -n '[ \t]+$' <이번 작업의 신규 파일>
결과: 추적 파일 오류 없음, 신규 파일 trailing whitespace 없음
```

첫 Compose 시도는 기존 프로세스가 사용 중인 호스트 `8080` 포트와 충돌해 시작하지 못했다. 기존 컨테이너를 중단하지 않고 `WEB_PORT=18081`로 재실행해 통과했으며, 작업용 Compose 컨테이너와 네트워크는 종료·제거했다.

## 6. 발견한 문제 / 남은 리스크

- `get_job_competency` MCP 도구는 아직 구현되지 않아 목표 다섯 도구 중 네 도구만 존재한다.
- 현재 운영 사용자 흐름은 기존 연습 기록 비교 API를 사용한다. 새 MCP 비교 도구는 내부 capability token 발급 경계를 통해 호출 가능하지만 별도의 사용자 공개 endpoint는 추가하지 않았다.

## 미확인 사항

- 운영 Supabase에 저장된 실제 사용자 1차·2차 `coaching_runs`로 live E2E를 수행하지 않았다.
- 운영 JWT와 배포된 `/mcp` URL에서의 인증·RLS·만료 차단은 확인하지 않았다.
- 이번 비교에는 실제 외부 LLM 호출이 없으므로 모델 품질·비용 검증 대상이 아니다.

## 7. 다음 작업

- 운영과 분리된 Supabase 테스트 데이터로 소유자 성공·타 사용자·만료·설정 불일치 live E2E를 수행한다.
- 남은 `get_job_competency` 도구의 Spec과 데이터 source를 확정한 뒤 구현한다.
