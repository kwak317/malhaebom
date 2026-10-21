# Worklog — PR #71 devset resume 검증

- 일시: 2026-09-28
- 작업자/에이전트: Codex
- 관련 PR: #71, #82

## 1. 목적

동일 행 수의 평가 데이터가 바뀌어도 기존 metrics를 재사용하는 경로를 차단한다.

## 2. 작업 전 상태

resume은 모델 출처·설정·행 수와 predictions 구조를 확인했으나 manifest와 오디오 내용은 비교하지 않았다.

## 3. 수행 내용

manifest SHA와 순서가 반영된 ID·오디오 SHA를 결합한 devset provenance를 preflight와 각 metrics에 기록하고 resume 비교에 포함했다. #82에서 제안한 helper의 입력·출력 계약을 현재 #71 베이스에 연결했다.

## 주요 판단과 이유

행 수가 같아도 참조문·오디오·행 순서가 다르면 이전 점수를 재사용할 수 없다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `backend/scripts/stt_real_user_eval_utils.py` | devset fingerprint |
| `backend/scripts/run_stt_real_user_matrix.py` | preflight·metrics·resume 연결 |
| `backend/tests/test_stt_real_user_matrix.py` | 변경 데이터 resume 거부 회귀 |
| `docs/experiments/stt/2026-09-28_real-user-model-beam-matrix.md` | 재현 조건 명시 |

## 5. 검증

- `python -m unittest backend.tests.test_stt_real_user_matrix backend.tests.test_stt_real_user_eval_utils -q`: 8개 통과.
- `git diff --check`: 통과.

## 6. 발견한 문제 / 남은 리스크

- #82와 같은 helper 변경이 PR diff에 중복되어 후속 stack 정리가 필요하다.

## 미확인 사항

- 실제 GPU 전체 matrix 재실행은 하지 않았다.

## 7. 다음 작업

- #82 diff와 base를 정리한다.
