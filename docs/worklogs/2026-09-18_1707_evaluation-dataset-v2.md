# Worklog — 평가 dataset/grader v2

- 일시: 2026-09-18 17:07 KST
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음; 기존 feat/llm-evaluation-foundation 브랜치에서 작업
- 관련 요구사항/결정: 사용자 승인 판정 수정안과 평가 v2 정책; docs/specs/coaching-evaluation-ops.md

## 1. 목적

기존 30건 정답과 핵심 15건 의미 annotation을 버전 분리하고 독립 의미/critical 지표를 채점한다. R/D 추가 및 실제 모델 호출 제외.

## 2. 작업 전 상태

이전 평가 기반의 uncommitted 변경을 보존했다. 작업 전 backend unittest 205개 통과.
기존 dataset에는 requirement text와 semantic annotation이 없었다.

## 3. 수행 내용

- dataset.jsonl v1 원본 보존; dataset.v2.jsonl에 승인된 30건 label과 15건 annotation 반영. 동일 질문/context 입력 보존.
- intent/C/A/V 독립 평가; v2 job alignment/status/job expected evidence를 고정 accuracy와 label consistency에서 제외.
- reason/action/question/hallucination별 사람 검토 0/1/2 rubric, 검토자/근거, 미검토 null 처리.
- annotation ID 검증, 질문 존재/action target 자동 검사와 의미 점수 분리.
- critical failure는 별도 검토/지표. 최종 case/run와 모든 call 집계로 재시도 전 실패 보존.
- runner 기본 v2 선택, 명시적 v1 지원, attempt별 review 연결 및 알 수 없는/미실행 attempt 거부, grader/version/hash 보존.

## 주요 판단과 이유

키워드나 mock 정답 출력으로 의미 품질을 자동 인증하지 않는다. 원문 대조 검토가 없는 항목은 분모에서 제외한다.
annotation은 사용자 승인 초안이며 독립 검토 미완료 provenance를 기록했다. expected/annotation/review는 실제 모델 입력으로 전달하지 않는다.

## 4. 변경 파일

- evals/dataset.v2.jsonl, coaching_dataset.py, semantic_grader.py, evaluation_records.py, run_model_comparison.py
- backend/tests/test_coaching_eval_v2.py
- evals/README.md, docs/specs/coaching-evaluation-ops.md, docs/CURRENT_STATE.md, docs/DECISIONS.md, 본 Worklog
- 이전 작업의 변경 파일/테스트/Worklog는 유지했다.

## 5. 검증

- /tmp/llm-eval-tests/bin/python -B -m unittest discover -s backend/tests: 기존+신규 213개 통과 (실제 LLM 호출 없음).
- python -B evals/run_model_comparison.py --candidate baseline=mock:expected --candidate degraded=mock:degraded --repeats 2 --output-dir /tmp/eval-v2-comparison: 30건×2후보×2run = 120건 mock 기록/JSON/Markdown 생성.
- git show HEAD:evals/dataset.jsonl 바이트 비교: v1 변경 없음. v1/v2 모든 질문/context 비교: 30건 입력 동일.
- git diff --check: 통과.
- 초기 신규 테스트의 future import 위치 및 criterion ID/원본 normal label fixture 오류를 수정하고 전체 재실행했다.

## 6. 발견한 문제 / 남은 리스크

프런트엔드 npm 실행 시 Windows npm이 WSL1 오류로 실패했다. Linux node symlink도 대상이 없어 프런트엔드 Vitest는 실행하지 못했다. 프런트엔드 의존성 설치/파일 변경 없음.

## 미확인 사항

실제 LLM 품질·가격·latency, 독립 annotation 검토, 실제 Supabase SQL/RLS 및 Docker heavy 통합 테스트는 수행하지 않았다. DB/모델 외부 서비스 호출은 없었다.

## 7. 다음 작업

독립 검토로 annotation/정답 신뢰도를 확인하고, 승인 후 실제 모델 비교 수행. 프런트엔드 테스트는 Linux Node.js 환경에서 별도 실행 필요.
