# Worklog — D11 운영 baseline과 preflight 정합성

- 일시: 2026-10-06 10:30 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: D11 baseline·약한 구간, 평가 입력/정답 독립성

## 1. 목적

최신 main에 이미 병합된 운영 이미지 30건×3회 raw 평가를 D11 체크포인트에 정확히 연결하고, 오프라인 preflight가 현재 기본 Prompt를 사용하도록 고친다.

## 2. 작업 전 상태

- `evals/results/2026-10-06-deployed-repeat3/`에 같은 운영 이미지·Dataset·Prompt·Skill의 90회 raw 결과와 해시가 있었다.
- 체크포인트 문서는 D11 baseline과 약한 구간을 여전히 미실행으로 기록했다.
- `evals/prepare_d11_baseline.py`는 현재 기본 v4와 달리 v5 Prompt 이름을 하드코딩했다.

## 3. 수행 내용

- preflight manifest의 Prompt 버전이 `DEFAULT_COACHING_PROMPT_VERSION`과 일치해야 한다는 실패 테스트를 먼저 추가했다.
- v5 문자열 하드코딩을 제거하고 coaching Prompt 모듈의 현재 기본값을 사용하도록 수정했다.
- 오프라인 manifest를 새 ignored 폴더에 생성해 Dataset 30건, v4 Prompt, Skill v6.1, paid run 미승인을 확인했다.
- 90회 aggregate에서 baseline과 지속 실패 유형을 체크포인트 문서에 연결했다.

## 주요 판단과 이유

- 새 provider 호출 없이 이미 보존된 운영 raw만 사용했다.
- 자동 통과율은 사람 semantic 품질로 표현하지 않는다.
- 신규 인젝션 입력·정답은 LLM으로 만들지 않았고, 신규 3건과 단일 변경 전후 실험은 미완료로 유지했다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `evals/prepare_d11_baseline.py` | 현재 기본 Prompt 버전 사용 |
| `backend/tests/test_prepare_d11_baseline.py` | 기본 Prompt 정합성 회귀 테스트 |
| `docs/project2-checkpoint-work-cards.md` | 운영 baseline·약한 구간 상태와 수치 연결 |
| `docs/experiments/2026-10-02_d11-baseline-preflight.md` | 후속 운영 baseline 및 현재 preflight 동작 기록 |
| `docs/CURRENT_STATE.md` | D11 현재 상태 갱신 |
| `docs/worklogs/2026-10-06_1030_d11-baseline-alignment.md` | 검증·판단·미완료 범위 기록 |
| `docs/worklogs/README.md` | Worklog 인덱스 |

## 5. 검증

```text
$env:PYTHONPATH = '.;backend;backend/tests'
python -m pytest backend/tests/test_prepare_d11_baseline.py -q
2 passed

python evals/prepare_d11_baseline.py --output-dir local-results/d11-baseline-preflight-20261006-1030
Model calls: 0; production match: NOT VERIFIED; paid run: NOT AUTHORIZED
dataset: 30 (normal 12 / boundary 10 / failure 8)
prompt: coaching-user-supplied-v4-verification
skill: interview-coach-v6.1-domain-rules

$env:PYTHONPATH = '.;backend;backend/tests'
python -m pytest backend/tests -q
593 passed, 1 failed, 264 subtests passed
실패: test_job_source_e2e_runner.py::test_reads_private_ignored_token_file
원인: Windows tempfile에 chmod(0o600)를 적용한 뒤 POSIX group/other mode를 검사하는 기존 테스트의 플랫폼 가정. 이번 D11 변경과 무관함.
```

## 6. 발견한 문제 / 남은 리스크

- 90개 새 출력의 사람 semantic·critical 평가는 수행하지 않았다.
- 현재 운영 baseline은 개선 전 기준이며 단일 변경 후 동일 조건 재측정이 없다.
- 전체 백엔드 회귀에서 Windows POSIX mode 가정에 의존하는 기존 테스트 1건이 실패했다. 나머지 593건과 264개 subtest는 통과했다.

## 미확인 사항

- 신규 인젝션 3건의 독립 사람 입력·정답·판정자
- 한 변수만 바꾼 개선 실험과 동일 조건 재측정
- 새 평가 run의 Langfuse Dataset/trace/Score 연결

## 7. 다음 작업

- 팀이 신규 인젝션 3건과 비용 상한을 승인한 뒤 단일 변경 전후 실험을 별도 브랜치에서 수행한다.
