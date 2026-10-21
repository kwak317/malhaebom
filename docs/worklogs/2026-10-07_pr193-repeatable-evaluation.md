# PR #193 평가 실행 결과 분리

- 검토 지적: 재실행이 기존 snapshot을 덮어쓰고 responses.jsonl을 누적함.
- 수정: --output-dir를 필수로 받아 새 폴더만 허용하고, 고정 snapshot 내부와 이미 존재하는 출력 폴더는 거부한다. 실행에 사용한 입력을 새 폴더로 복사한다.
- 검증: 모델 호출 없이 두 독립 폴더 초기화, 기존 폴더 재사용 거부, snapshot 출력 거부, 원본 전체 파일 hash 불변 확인 통과.
- 원래 evals/results 안의 실행 파일은 당시 증거와 hash 보존을 위해 유지하며, 재실행은 docs/evidence 안의 수정된 runner를 사용한다.
