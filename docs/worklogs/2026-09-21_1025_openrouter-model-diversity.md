# Worklog — OpenRouter 모델 계열 다양성 평가

- 일시: 2026-09-21
- 작업자/에이전트: Codex
- 관련 Spec: [OpenRouter 모델 다양성 평가](../specs/openrouter-model-diversity-evaluation.md)
- 관련 실험: [OpenRouter 모델 계열 다양성 평가](../experiments/2026-09-21_openrouter-model-diversity.md)

## 1. 목적

기존 30건 평가 하네스를 재사용해 현재 OpenRouter key로 접근 가능한 서로 다른 개발사 모델을 discovery→smoke→preflight→전체 평가 순서로 비교한다.

## 2. 작업 전 상태

고정 6종 runner와 Basic/Premium 실험별 script가 있었지만 인증된 모델 discovery, 개발사 다양성 선택, preflight gate, 탈락 모델 포함 통합 CSV/JSON/Markdown은 없었다. 작업 트리는 최신 main을 반영한 기능 브랜치에서 깨끗했다.

## 3. 수행 내용과 판단

- Why/Goal/What/How/AC Spec을 먼저 작성했다.
- `/models/user` 응답의 안전한 모델 metadata만 저장하고 key 및 provider 원문 오류는 저장하지 않았다.
- text 단독 출력·`response_format` 지원을 요구하고 batch/router/safeguard 전용 모델을 제외했다.
- stable alias의 `canonical_slug` 차이는 중복으로 오판하지 않았고 `~anthropic` 형태는 원 개발사로 집계했다.
- 3개 모델 smoke 뒤 30개 개발사 후보 preflight를 수행했다.
- PASS15개만 30건씩 실행했다. queue를 개발사 round-robin으로 바꿔 특정 provider 편중을 줄였다.
- 호출별 atomic JSON과 재개 동작으로 driver 중단 전 결과를 재사용했다.

## 4. 변경 파일

- `evals/run_openrouter_diversity.py`
- `evals/openrouter_diversity.py`
- `backend/tests/test_openrouter_diversity.py`
- `docs/specs/openrouter-model-diversity-evaluation.md`
- `docs/experiments/2026-09-21_openrouter-model-diversity.md`
- `evals/README.md`
- `docs/CURRENT_STATE.md`
- 본 Worklog
- Git 제외 결과: `local-results/openrouter-diversity-20260921-v2/`

리뷰 가능한 human-authored diff 400줄 원칙을 지키기 위해 공통 모듈·테스트 PR과 실행 CLI·문서 PR을 stacked PR로 분리했다.

## 5. 검증과 결과

- discovery 283, eligible 214, 선택/preflight 30, PASS 15, 30건 완료 15.
- 본평가 450/450 고유 사례 파일 저장.
- 알려진 총비용 $8.2166702564, 비용 미확인 67호출.
- `.venv-llm-eval`: 신규4 + 기존 coaching eval5 = 9테스트 통과.
- `python -m py_compile evals/run_openrouter_diversity.py`, `git diff --check` 통과.
- 변경 파일을 현재 `OPENROUTER_API_KEY` 값과 대조한 secret scan 통과(값은 출력하지 않음).
- 평가 전용 venv의 backend 전체 discovery는 FastAPI/JWT/NumPy 부재로 21개 import error가 발생했다.
- 기존 `/tmp/llm-eval-tests` 전체 suite는 180초 동안 FastAPI/TestClient 구간에서 완료되지 않아 timeout 124로 종료했다. 이번 변경 관련 테스트 실패는 없지만 전체 suite 통과로 보고하지 않는다.

## 6. 발견한 문제 / 미확인 사항

- preflight PASS 뒤 전체 평가에서 계약 위반과 rate limit이 발생했다.
- 일부 자동 routing 응답 지연이 설정한 SDK timeout보다 길었다.
- 사람 semantic 검토는 수행하지 않아 semantic 결과는 null이다.
- 비용 미확인 호출은 실제 비용 0으로 간주하지 않는다.
- Cohere는 현재 목록에서 structured output 조건을 만족하는 후보가 없어 실행하지 못했다.

## 7. 다음 작업

사람 semantic 검토가 필요하면 기존 rubric으로 모델·case subset을 먼저 정하고 별도 실행한다. 이번 결과만으로 운영 모델을 변경하지 않는다.
