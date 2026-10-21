# Worklog — B0/C2 STT 모델 Drive 인계

- 일시: 2026-10-01
- 작업자/에이전트: Codex
- 관련 이슈/PR: 없음
- 관련 요구사항/결정: B0/C2 실험 모델 인계; legacy 모델과 서비스 기본 모델 유지

## 1. 목적

선택된 B0/C2 adapter와 CT2 전체를 각각 원본 ZIP으로 인계하고, 설정·평가·검증 방법을 Markdown으로 정리한다.

## 2. 작업 전 상태

- 최초 `git status --short --branch`: `main...origin/main`, 미커밋 변경 없음.
- B0 설정의 `output_dir`은 도구 출력에서 `[REDACTED]`로 표시됐다. 실험 기록, C2 학습 설정의 `init_adapter`, retention runner를 대조해 로컬 B0 경로를 확인했다.
- 기존 Drive 폴더에는 인계 문서가 있었다. 앞선 업로드 시도에서 생성한 분할 파일과 안내는 사용자 지시에 따라 제거했다.

## 3. 수행 내용

- B0/C2 `best_adapter/` 전체와 CT2 전체를 각각 별도 ZIP에 넣고, 각 ZIP에 README, 학습 설정, 실험·평가 근거, `SHA256SUMS.txt`를 포함했다.
- ZIP 두 개를 기준으로 `artifacts/stt/handoff-20261001/README.md`를 작성하고 Drive에 업로드했다.
- 앞선 시도에서 생성한 Drive 조각 파일 34개 및 조각 전용 `PARTS-SHA256SUMS.txt`, `UPLOAD-README.txt`를 삭제했다. 로컬에서도 같은 조각 파일 34개와 조각 전용 파일 2개를 삭제했다.
- 기존 Google Docs 인계 가이드의 조각 업로드 설명을 원본 ZIP 두 개 기준으로 수정했다.

## 주요 판단과 이유

- adapter와 CT2는 ZIP 내부에서 별도 디렉터리로 유지했다. B0와 C2도 각각 독립된 ZIP이다.
- 학습 원본 데이터, 음성·전사, checkpoint, optimizer/scheduler state, 개인정보 파일은 포함하지 않았다.
- 기존 legacy Drive 모델, 현재 서비스 기본 모델, 공유 권한은 변경하지 않았다.

## 4. 변경 파일

| 파일 | 변경 내용 |
| --- | --- |
| `artifacts/stt/handoff-20261001/B0-Clean-Continuation.zip` | B0 인계 ZIP, 로컬 Git ignore 대상 |
| `artifacts/stt/handoff-20261001/C2-Interview-Domain.zip` | C2 인계 ZIP, 로컬 Git ignore 대상 |
| `artifacts/stt/handoff-20261001/ARCHIVE-SHA256SUMS.txt` | 두 ZIP의 SHA256 |
| `artifacts/stt/handoff-20261001/README.md` | 원본 ZIP 두 개 기준 인계 설명; Drive에도 업로드 |
| `docs/worklogs/2026-10-01_stt-b0-c2-drive-handoff.md` | 작업 기록 |
| Google Docs 인계 가이드 | 원본 ZIP 업로드 상태로 문장 갱신 |

## 5. 검증

- B0: adapter 22,861,325 bytes, CT2 1,532,907,663 bytes; ZIP 1,555,782,541 bytes. ZIP 내 17개 데이터 파일 모두 원본 SHA256과 일치.
- C2: adapter 22,861,261 bytes, CT2 1,532,907,663 bytes; ZIP 1,555,790,246 bytes. ZIP 내 19개 데이터 파일 모두 원본 SHA256과 일치.
- C2 adapter SHA256 `fdf46fdadc42f70f3e30e5d57c5a5697ae6193f5550fc52b0754c2fcbd842d23`, CT2 fingerprint `51610f03f726317e428bf1fc3fb7528189735b2656bbc4dacf47699933072966`: frozen selection JSON과 일치.
- `sha256sum -c ARCHIVE-SHA256SUMS.txt`: B0/C2 ZIP 모두 OK.
- Drive 폴더 재조회: 원본 B0 ZIP 1,555,782,541 bytes, C2 ZIP 1,555,790,246 bytes, `README.md`, `ARCHIVE-SHA256SUMS.txt`, 기존 인계 문서 존재. 조각 및 조각 전용 설명 파일은 0개.
- Google Docs `replaceAllText`: 상태 문장 1곳 변경.

## 6. 발견한 문제 / 남은 리스크

- Drive 목록·크기 확인은 원격 바이트 SHA256 검증이 아니다. 수신자가 다운로드 후 체크섬을 확인해야 한다.
- 이번 인계 작업에서 STT 모델 추론을 재실행하지 않았다. README의 성능 수치는 기존 실험 기록이다.

## 미확인 사항

- Drive에서 다운로드한 ZIP의 SHA256, 수신 환경의 모델 로드·음성 추론.

## 7. 다음 작업

- 수신자가 `README.md`의 순서대로 ZIP 다운로드·해시 확인·추론을 수행한다.
