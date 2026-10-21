# 로컬 CPU 이미지 재현 점검 (2026-10-10)

## 후보 및 범위
운영 Dockerfile/배포 설정/backend STT 코드는 그대로 유지한다. 로컬 Compose만 Dockerfile.local-cpu와 CPU/int8을 사용한다. torch/torchaudio 2.8.0은 공식 CPU index에서 설치하고 constraints로 고정한다. PyAV 19의 STT 호출 비호환을 실제 WAV로 확인하여 로컬만 av==16.1.0으로 고정했다. 로컬 프런트 Dockerfile은 정적 소개 HTML을 명시적으로 복사한다. STT 모델은 기존 large-v3-turbo다.

새 remote clone에 미커밋 후보 Dockerfile.local-cpu, backend/constraints-local-cpu.txt, docker-compose.yml, .env.example을 적용했다. main에 반영된 버전의 검증이라고 주장하지 않는다. 새 docker-container builder로 기존 빌드 레이어 캐시를 사용하지 않는다. Docker Desktop / Compose v5.5.0 / Linux ARM64 환경, 포트 18300/18380, provider 키 없이 STT warmup 비활성화.

## 기동 결과
**최종 후보 통과: clone부터 두 서비스 healthy까지 394.86초(6분 34.86초).** API health HTTP 200은 380.48초, 실제 소개와 연습 HTML HTTP 200은 각각 384.51초였다. 소개 문구/hero-heading, React root를 검사했고 브라우저에서 소개→연습 로그인 안내 표시를 확인했다. Supabase 키를 넣지 않아 실제 Google 로그인은 수행하지 않았다.

검증 전에 Docker와 새 독립 BuildKit builder를 실행 가능한 상태로 준비했다. 그 준비 시간은 측정에서 제외했다. 해당 builder에 기존 base/apt/pip/npm/앱 빌드 캐시를 가져오지 않았고, 로그에서 기본 이미지 다운로드와 전체 의존성 설치를 확인했다. Docker에 11 CPU·약 7.75GiB 메모리가 할당된 ARM64 환경이다. 다른 PC·네트워크에서 동일 시간을 보장하는 결과는 아니다.

## STT/VAD 결과
**최종 이미지에서 통과.** 기존 공개 모델 캐시를 SHA256 확인 후 복사하고 HF_HUB_OFFLINE=1로 실행했다. 7.184초·16kHz·mono·16bit 합성 한국어 WAV의 전사 12.614초, 모델 로딩/VAD 포함 32.55초. 입력과 같은 문장, 11단어 시간 정보, 전사 2구간, VAD 3구간을 확인했다. 실제 사용자 음성 정확도 및 로그인→DB→코칭 전체 E2E는 별도다.

전사문: “안녕하세요. 저는 백엔드 개발자 면접을 준비하고 있습니다. 프로젝트에서 로그인 오류를 수정했습니다.”

PyAV 16.1.0, torch 2.8.0+cpu, torchaudio 2.8.0, torch.version.cuda=null, NVIDIA/CUDA Python 패키지 없음, pip check 통과. 모델 repository mobiuslabsgmbh/faster-whisper-large-v3-turbo / revision 0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf / model.bin SHA256 e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da.

[원본 수치·파일 hash](local-cpu-reproduction-20261010.json)와 [재검사 스크립트](../../scripts/check_local_cpu_stt.py)를 따른다.

## 공식 패키지 근거
[PyTorch CPU wheel 목록](https://download.pytorch.org/whl/cpu/torch/)과 [TorchAudio wheel 목록](https://download.pytorch.org/whl/cpu/torchaudio/)에서 Python 3.12용 ARM64/x86_64 파일을 확인했다. 파일 존재 확인은 다른 PC에서의 실행 검증이 아니다.

## 실패와 수정 이력
- 최초 CPU 후보: healthy까지 605.71초. API 591.32초, 연습 HTML 596.36초에 HTTP 200이었으나 루트는 Nginx 기본 페이지여서 제품 재현 통과로 처리하지 않았다.
- 소개 HTML 포함 후 재측정 후보는 PyAV 19 비호환 발견으로 중단했다. 최종 후보는 로컬 프런트 전용 Dockerfile 및 av==16.1.0을 적용하고 다시 새 clone/독립 builder로 측정한다.
- 첫 모델 다운로드는 Xet 경로에서 진행이 멈췄다. 로컬에만 HF_HUB_DISABLE_XET=1로 HTTP 경로를 적용했고 일부 파일 전송은 확인했다. 전체 1.62GB 다운로드 완료 시간은 검증하지 않았다. STT 동작은 동일 공개 모델의 SHA256을 확인한 기존 캐시로 검증한다.
- [Hugging Face 공식 환경 변수](https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables)는 Xet 사용 비활성화를 지원한다.
