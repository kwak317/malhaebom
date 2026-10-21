# Overnight jobs

장시간 fine-tuning, evaluation, model/data download를 SSH/터미널 연결과 분리해서 실행하기 위한 공통 운영 도구다.

## 원칙

- `tmux` detached session에서 실행한다.
- stdout/stderr는 `artifacts/overnight/<job>/<run-id>/run.log`에 보존한다.
- 실행 상태, PID, 종료 코드도 같은 run directory의 `state.json`에 남긴다.
- 같은 job 이름의 tmux session이 살아 있으면 중복 실행을 거부한다.
- resume 가능한 학습 job은 해당 실험 output의 최신 checkpoint만 이어서 사용한다.
- `artifacts/`는 gitignore 대상이다.
- Windows가 절전/재부팅되면 tmux만으로는 작업을 계속할 수 없다. `doctor`로 AC 절전 설정을 확인한다.

## 기본 사용

```bash
python3.12 backend/scripts/overnight_job.py doctor
python3.12 backend/scripts/overnight_job.py list

# STT full fine-tuning
python3.12 backend/scripts/overnight_job.py start stt-finetune-full

# clean continuation
python3.12 backend/scripts/overnight_job.py start stt-clean-continuation

# Test B 3-way evaluation
python3.12 backend/scripts/overnight_job.py start stt-test-b-three-way

# 전체 상태
python3.12 backend/scripts/overnight_job.py status

# 특정 job 로그
python3.12 backend/scripts/overnight_job.py logs stt-clean-continuation --lines 80

# 필요 시 중지
python3.12 backend/scripts/overnight_job.py stop stt-clean-continuation
```

`start` 결과에는 run log 경로와 tmux attach 명령도 출력된다.

개발자 로컬 Makefile에 alias를 둘 수 있지만 Makefile은 저장소 추적 대상이 아니다. 따라서 문서와 `configs/overnight_jobs.json`은 직접 Python 명령을 canonical 실행 경로로 사용한다.

## 등록된 job

- `stt-finetune-full`: Whisper Medium QLoRA fresh retrain. checkpoint 자동 재개 가능.
- `stt-clean-continuation`: retrain best adapter에서 placeholder-free manifest로 LR 2e-5, 0.5 epoch 추가 학습. 새 output checkpoint 자동 재개 가능.
- `stt-test-b-three-way`: clean Test B 500개를 baseline / 1차 retrain / clean continuation 모델에 순차 평가하고 비교 JSON을 생성한다.
- `stt-convert-ct2`: retrain best adapter merge + CT2 float16 변환.
- `model-envs-bootstrap`: 모델 venv 구성/패키지 다운로드.
- `self-test`: detached runner 자체 테스트.

## 데이터 다운로드 job 추가

새 다운로드 script가 준비되면 `configs/overnight_jobs.json`에 argv를 등록한다. URL, token, API key 같은 secret은 JSON에 넣지 말고 environment 또는 gitignored local config에서 읽게 한다.

## 장애 대응

SSH/터미널이 끊겨도 tmux session과 실제 child process는 계속 실행된다. status에서 `running_without_tmux`가 보이면 child는 살아 있으므로 로그를 확인하거나 `stop`으로 process group을 종료한다.

`stt-finetune-full`과 `stt-clean-continuation`은 checkpoint에 adapter, optimizer, scheduler, RNG, trainer state를 함께 저장하며 `resume=auto`다. 동일 job을 다시 시작하면 해당 실험 output의 최신 checkpoint에서 재개한다.

Windows 절전/재부팅은 tmux가 해결할 수 없다. 시작 전 아래 명령으로 AC 절전 설정을 확인한다.

```bash
python3.12 backend/scripts/overnight_job.py doctor
```
