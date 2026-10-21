# Worklog — 6종 LLM 평가 기반

- 일시: 2026-09-18 16:19 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 미생성; 브랜치 feat/llm-evaluation-foundation
- 관련 요구사항/결정: 사용자 승인 범위, coaching-evaluation-ops AC-09/10

## 1. 목적

6종 평가 설정과 호출 기록·세부 grader·consistency·Premium 부모 참조를 구현하고 mock만 검증한다.

## 2. 작업 전 상태

clean main. 기존 평가 테스트 4개 통과. runner는 JSON mode/temperature 0,
가격표 추정 비용만 사용하고 parse/validator 실패 시 비용을 잃었다.

## 3. 수행 내용

- 6개 정확한 ID와 basic/premium 분류, strict schema/require_parameters/자동 routing 적용.
- temperature/reasoning 미전송 정책 기록. SDK retry 0, 명시적 max-calls 호출별 기록.
- raw/parsed/validated 출력, 단계 결과, generation/provider/model/전체 usage·실제 비용 보존.
- label별 판정과 evidence/ID 점수, case별 유효 label pair consistency, 부모 실행 참조 추가.
- dataset/grader/schema/config 해시와 model ID, 기존 Prompt/Skill 버전 기록.

## 주요 판단과 이유

usage.cost 미제공은 unknown으로 유지. 합계는 알려진 비용만 합산하고 미확인 호출 수를 보고한다.
Premium 자동 fallback/의미 품질 grader/dataset 추가는 범위 밖이다. 동일 입력 재요청이며 repair prompt는 미구현.

## 4. 변경 파일

- evals/run_model_comparison.py, evals/evaluation_records.py: 설정·기록·집계
- evals/coaching_dataset.py: 세부 label 판정
- backend/tests/test_evaluation_records.py: mock 회귀 5개
- evals/README.md, docs/specs/coaching-evaluation-ops.md, docs/CURRENT_STATE.md, 본 Worklog

## 5. 검증

- 기존 평가 baseline: python -B -m unittest discover -s backend/tests -p 'test_coaching_eval.py': 4 PASS.
- 기본 Python 전체 실행: FastAPI 부재로 17 import ERROR. 변경과 무관한 환경 문제.
- /tmp/llm-eval-tests 격리 환경에 경량 테스트 의존성 설치. sandbox 설치는 DNS 실패,
  승인된 network escalation으로 설치 성공. ML 의존성·모델 다운로드 없음.
- 테스트 환경 Python 3.14, FastAPI 0.115.12, PyJWT 2.10.1, multipart 0.0.20,
  MCP 1.27.2, OpenAI SDK 2.54.0. 저장소 의존성 변경 없음.
- sandbox 전체 실행은 로컬 TestClient 대기 상태여서 중단. 60초 제한의 escalated mock 회귀 실행:
  /tmp/llm-eval-tests/bin/python -B -m unittest discover -v -s backend/tests: 205 PASS (2.869s).
- mock CLI expected/degraded, repeats=2: 30×2×2=120 호출, /tmp/llm-eval-smoke JSON/Markdown 생성 PASS.
- git diff --check: PASS.

## 6. 발견한 문제 / 남은 리스크

공고 텍스트/R/D 기준 부재, 독립 정답 출처와 의미 품질 채점은 기존 한계다.
provider가 응답에 없으면 null. 실제 provider metadata 보충 조회는 미실행·미구현.
현재 변경은 문서 포함 400줄을 넘으므로 향후 PR은 기록/runner와 grader/검증 책임 단위로 분리해야 한다.

## 미확인 사항

실제 6종 API 지원/usage/provider 반환, 3.12 환경, 모델 품질 및 Premium recovery 미검증.

## 7. 다음 작업

사용자 승인 후 실제 비교 실행과 의미 품질 rubric/dataset 보완을 별도 진행한다.
