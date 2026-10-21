# Worklog — overnight long-job runner

- 일시: 2026-09-20
- 목적: fine-tuning, evaluation, 향후 data/model download를 터미널 연결과 분리해 밤새 안전하게 실행할 수 있는 공통 runner 준비

## 환경 확인

- WSL에서 tmux 사용 가능
- systemd user bus는 사용할 수 없음
- nohup/setsid 사용 가능
- Windows 현재 AC 절전 timeout: 0초(절전 안 함)
- artifacts directory는 gitignore 대상

## 구현

- `backend/scripts/overnight_job.py`
  - registered job start/list/status/logs/stop/doctor
  - tmux detached execution
  - per-run log/state
  - duplicate live session 방지
  - child PID/process group 기록 및 stop
  - GPU snapshot
  - Windows sleep setting 확인
- `configs/overnight_jobs.json`
  - STT training/evaluation/conversion 및 environment bootstrap 등록
  - future download job 등록 가능
- Makefile convenience targets 추가
- 운영 문서 `docs/operations/overnight-jobs.md` 추가

## 검증

- `make overnight-doctor`: PASS
  - tmux `/usr/bin/tmux`
  - disk free 약 700 GiB
  - RTX 5070 Ti 확인
  - Windows AC sleep 0초(절전 안 함), DC 600초
- `make overnight-self-test`: PASS
  - detached tmux session에서 시작
  - 별도 child PID/process group 기록
  - 약 2초 후 exit code 0으로 완료
  - tmux session 종료 후 state가 `completed`, child/tmux 모두 inactive로 확인
- run log에 START/cwd/argv, 실시간 stdout, END/exit code가 정상 기록됨
