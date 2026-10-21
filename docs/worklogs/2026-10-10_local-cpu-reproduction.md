# 로컬 CPU 이미지와 새 clone/STT 재현

## 요청과 범위
운영 설정을 유지하고 로컬 재현용만 CPU 전용 이미지로 변경한다. 새 clone 기동 10분 기준과 실제 STT를 확인하고 README에 반영한다. 기존 저장소 정리 미커밋 변경을 보존했다.

## 변경
Dockerfile.local-cpu, backend/constraints-local-cpu.txt 추가. 로컬 Compose의 Dockerfile과 CPU/int8 선택을 변경했다. frontend/Dockerfile.local-reproduction에서 정적 소개 HTML을 dist에 복사한다. torch/torchaudio 2.8.0을 공식 CPU index에서 설치하고 requirements 설치에도 constraints를 적용한다. 실제 WAV로 PyAV 19 비호환을 확인해 로컬 constraints에 av==16.1.0을 고정했다. Xet 모델 다운로드 정체로 로컬에 HF_HUB_DISABLE_XET=1을 적용했다. pip check와 torch CUDA/NVIDIA Python 배포 패키지 부재 검사를 이미지 빌드에서 수행한다. 개인정보 없는 WAV의 실제 서비스 STT/VAD smoke를 위한 scripts/check_local_cpu_stt.py 추가.

## 검증
새 remote clone에 후보 파일을 적용하고 새 docker-container builder로 기존 빌드 캐시 없이 측정 완료. 운영 Dockerfile과 .github/backend/app/configs/frontend/Dockerfile에 변경 없음. Compose 문법·문서 링크·스크립트 문법 검사 통과. 호환 버전의 CPU prototype에서 합성 7.184초 WAV를 11.223초에 전사, 모델 로딩/VAD 포함 22.374초, 입력과 같은 문장·11단어·2전사구간·3 VAD 구간 확인. 기존 공개 모델 캐시의 SHA256을 검증한 테스트이며 첫 모델 전체 다운로드 완료는 미검증이다. 최종 이미지에서도 통과: 6분 34.86초 healthy, 실제 소개/연습 표시와 API 확인, 전사 12.614초·로딩/VAD 포함 32.55초. 상세 결과는 [증거](../evidence/local-cpu-reproduction-20261010.md)에 기록한다.

## 경계
운영 배포/트래픽/비밀값과 Prompt/Skill/STT 모델은 바꾸지 않는다. 실제 provider 키를 사용하지 않으며 인증 브라우저·DB·코칭 E2E는 별도다. 사용자가 후속으로 이번 폴더 정리와 README를 함께 PR 생성·merge하도록 승인했다. 운영 배포는 요청 범위에 포함하지 않는다.
