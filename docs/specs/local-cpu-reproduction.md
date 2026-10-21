# 로컬 CPU 재현 이미지

## Why
로컬 CPU 실행에도 Silero VAD의 간접 의존성이 GPU PyTorch/NVIDIA 패키지를 설치해 새 clone 기동이 10분을 넘겼다.

## Goal
로컬 Compose만 CPU 전용 이미지로 실행하고 운영 Dockerfile·배포 설정·STT 모델은 유지한다.

## What / How
Dockerfile.local-cpu와 CPU PyTorch/TorchAudio 2.8.0·호환 PyAV 16.1.0 constraints를 추가한다. CPU 전용 공식 wheel 저장소에서 먼저 설치하고 전체 requirements 설치에도 constraints를 적용한다. Compose는 새 Dockerfile과 CPU/int8을 사용한다. 이미지 빌드에서 torch CUDA 지원·NVIDIA 패키지 부재를 검사한다. 새 remote clone에 미커밋 후보 파일만 적용하여 독립 빌드 캐시에서 기동 시간을 측정한다. 현재 모델 large-v3-turbo로 실제 한국어 WAV STT/VAD를 검사한다.

## AC
- 운영 Dockerfile/배포 workflow/backend STT 코드·모델 기본값 변경 없음.
- torch.version.cuda is None, NVIDIA/CUDA 배포 패키지 없음, pip check 통과.
- 새 clone 후보의 웹/API healthy 및 HTTP 200까지 600초 이내인지 실측.
- CPU/int8 large-v3-turbo에서 한국어 음성의 전사·시간 정보와 VAD 구간 확인.
- README에 시작/모델 다운로드 시간 및 인증 E2E와 구분한 검증 범위 기록.

## 실제 기동에서 발견한 로컬 프런트 문제
Vite build는 module script 없는 루트 정적 소개 HTML을 dist에 내보내지 않아 기존 frontend Docker 이미지의 Nginx 기본 index가 노출됐다. 운영 frontend/Dockerfile은 유지하고 로컬 전용 Dockerfile.local-reproduction에서 정적 index.html을 dist에 복사한다. HTTP 200뿐 아니라 소개 문구와 React entry/실제 JS asset을 확인한다.
