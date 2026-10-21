# 새 clone Compose 재현성 점검

## 기준
사용자가 제시한 필수 기준은 clone → .env.example 복사 및 키 입력 → docker compose up, 로컬 기동 10분 이내와 README 절차다.

## 검증 환경
main e6ecc4b 새 shallow clone. Docker Desktop / Compose v5.5.0 / linux arm64 이미지. 기존 checkout·node_modules·운영 환경값·운영 이미지를 사용하지 않는다. Docker base/apt layer 캐시는 일부 존재한다. pip/npm 의존성 설치와 앱 빌드는 새로 실행한다.

작업 중 예제 환경 변경은 Skill 버전 v6 정합화와 STT 사전 다운로드 비활성화다. 테스트용 포트는 충돌 방지를 위해 WEB_PORT=18380/API_PORT=18300. 실제 provider 키는 넣지 않았으며 STT 모델·실음성·Supabase 사용자 로그인/DB 전체 흐름을 검증하지 않는다.

## 결과
**10분 이내 기동 기준 미충족.** 새 clone에서 시작한 최초 빌드는 600초 시점에도 API 이미지 layer export 단계였다. 약 616.6초(10분 16.6초)에 해당 검증만 중단했다(exit 130). pip 설치 단계는 약 493.3초였다. API/웹 컨테이너 기동·healthy·HTTP 응답은 이번 검증에서 확인하지 못했다.

실행 명령은 `docker compose --project-name malhaebom-clean-repro-1010 up --build --detach --wait --wait-timeout 150`이었다. `--wait-timeout`은 최초 이미지 빌드 전체 시간을 제한하지 않으므로 10분 기준을 별도 관찰했다. Docker base/apt 캐시가 일부 있었음에도 이 환경에서 기준을 넘겼다. README의 기본 `docker compose up`도 새 이미지가 필요하므로 이 최초 빌드 문제를 피하지 못한다. 예제 환경의 STT warmup 비활성화만으로 의존성 설치 시간을 해결할 수는 없다.

## 제출 전 남은 확인
- 로컬 Compose는 CPU STT 구성인데 Silero VAD의 간접 의존성으로 torch와 NVIDIA CUDA 패키지가 설치된다. ARM64 최초 설치에서 대용량 다운로드를 확인했다. CPU 전용 의존성 고정과 완전 무캐시 재검증은 이번 문서/자산 정리와 별도 실행환경 개선 항목이다.
- 실제 제공할 키/DB 환경에서 로그인 → 음성 분석 → 코칭을 재현해야 한다. 이번 빈 키 health 점검만으로 전체 서비스 재현 완료라고 표시하지 않는다.
