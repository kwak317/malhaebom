# 준비 대화 v3.1 로컬 평가 원본

12개 수작업 합성 시나리오 × 3회, 총 96개 실제 provider 응답. 자동 계약/서버 검사 36/36이며 사람 의미 품질 완전 통과를 뜻하지 않는다. 원본 manifest의 hash와 과거 실행 환경을 보존한다. 제품 API·DB·로그인·운영 검증 자료가 아니다.

재실행은 `OPENROUTER_API_KEY` 또는 `COACHING_LLM_API_KEY`를 환경에 두고 `run_eval.py`를 실행한다. 실행하면 이 폴더 결과를 갱신하므로 별도 복사본에서 실행한다. Python openai 1.109.1, jsonschema 4.26.0, pydantic 2가 필요하다. 유료 API를 호출한다. 서버 정책 snapshot은 당시 평가 고정용이며 운영 코드의 대체물이 아니다.

원본 응답·기계 생성 결과·당시 Prompt/Skill/서버 정책 snapshot은 `evals/results/preparation-dialogue-v3.1-20261006/`에 보관한다. 수작업 시나리오와 재현 절차·실행 코드는 이 문서 폴더에서 검토한다. 재실행 시 저장소 전체를 별도로 복사해서 두 경로를 함께 유지한다.

재실행은 `python docs/evidence/preparation-dialogue-v3.1-20261006/run_eval.py --output-dir local-results/preparation-run-새이름`으로 실행합니다. 출력 경로는 매번 새 디렉터리여야 하며 frozen snapshot 내부·기존 경로는 거부합니다. 입력 snapshot과 최초 결과는 보존되고 집계는 새 실행 결과만 읽습니다. `evals/results/`의 기존 runner는 당시 원본 증거이며 재실행용이 아닙니다.
