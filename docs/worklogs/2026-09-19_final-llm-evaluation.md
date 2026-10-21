# Worklog — LLM 6종 평가 최종 정리

- 일시: 2026-09-19
- 작업자/에이전트: Codex
- 관련 이슈/PR: 현재 작업 PR
- 관련 요구사항/결정: `EVAL_REPORT.md`, `docs/DECISIONS.md`

## 1. 목적

정책 정렬, Basic 전체 평가, Premium recovery와 63개 사람 semantic 검토를 하나의 최종 모델 선정
근거로 정리하고 재현 코드·테스트와 함께 PR로 제출한다.

## 2. 작업 전 상태

dataset v2, Skill/grader 정렬, Basic90회, Premium recovery24회와 review packet은 완료됐지만
사람 semantic 수치와 최종 후보 판단은 canonical 평가 리포트에 반영되지 않았다.

## 3. 수행 내용

- 사람 semantic 결과와 strict blind 범위를 문서화했다.
- Basic 자동 품질·semantic·critical·latency·비용을 함께 비교했다.
- Premium recovery·semantic·복구당 비용·recovery latency를 함께 비교했다.
- Gemini/DeepSeek Basic 후보, GPT Terra fallback, Qwen 제외 결론을 기록했다.
- case20, Premium instrumentation failure, failure subset 편향과 R/D 미완료를 명시했다.
- 전체 변경의 테스트·diff·secret/ignore 상태를 검사하고 commit/push/PR을 준비했다.

## 주요 판단과 이유

자동 label만으로 코칭 근거와 행동의 의미 품질을 판단할 수 없어 사람 검토를 분리했다.
Premium은 Basic 실패 subset이므로 semantic 절대값을 Basic과 직접 비교하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `EVAL_REPORT.md` | 6종 최종 결과·비용·latency·사람 검토·결론·한계 |
| `docs/DECISIONS.md` | Basic/Premium 후보 결정 |
| `docs/CURRENT_STATE.md` | 현재 평가 완료 상태 |
| `evals/README.md` | semantic 검토 범위와 최종 결론 |
| `docs/worklogs/2026-09-19_final-llm-evaluation.md` | 최종 작업 기록 |

## 5. 검증

```text
PYTHONPATH=.:backend:backend/tests /tmp/llm-eval-tests/bin/python -m unittest discover -s backend/tests -p 'test_*.py'
226 tests passed in 2.178s

.venv-llm-eval/bin/python -B evals/run_model_comparison.py --candidate baseline=mock:expected --candidate degraded=mock:degraded --output-dir /tmp/llm-eval-final-mock
mock comparison JSON/Markdown 생성 성공

.venv-llm-eval/bin/python -m pip check
No broken requirements found

npm test -- --run
현재 WSL 1에서 Node.js install directory를 찾지 못해 테스트가 시작되지 않음

git diff --check
통과

git diff --cached --check
통과

staged secret scan
실제 키 패턴 없음. `.env`, `local-results/`, `.venv`, cache 파일은 staged 목록에서 제외됨

최신 origin/main 병합 후 회귀 검증
229 tests passed in 2.177s; mock comparison JSON/Markdown 생성 성공
```

## 6. 발견한 문제 / 남은 리스크

- 63개 전체가 strict blind는 아니다.
- Premium semantic은 failure subset 결과다.
- case20은 known ambiguous다.
- 최초 Premium case13 3회 비용은 instrumentation failure로 미확인이다.
- R/D·requirement context·반복 consistency·검토자 간 일치도는 미완료다.

## 미확인 사항

- 실제 운영 traffic과 Langfuse 배포 trace의 품질·비용·지연.

## 7. 다음 작업

- 운영 후보 설정 후 반복 측정과 R/D/requirement context 평가를 추가한다.
