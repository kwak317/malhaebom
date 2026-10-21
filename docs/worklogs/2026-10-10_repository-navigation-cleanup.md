# 저장소 안내·인덱스·미사용 자산 정리

목적: 사용자 승인한 README → 문서 안내 → 평가 안내 → 미사용 파일 순서로 정리.
작업 전: main e6ecc4b, frontend/.gitignore CLI 생성 파일은 기존 상태로 보존. README에 예전 revision, 평가 안내에 v5 기본값 문구, Worklog 목록 일부 누락, 과거 공개 데모 WebP 4개 미참조.
수행: README 최신 주소/기능/자료 입구, docs 최신/과거 안내, Worklog 전체 인덱스, evals 운영/후보/results 안내. 미참조 WebP 4개만 archive로 원본 보존 이동.
판단: 실행/재현 참조를 지키기 위해 문서·평가 원본·후보는 이동/삭제하지 않음. 사용 중인 데모 PNG는 유지. 중요한 코드/설정 폴더는 변경하지 않음.
검증: 기존 유지 문서 7개 링크 검사, 신규 인덱스/보관/후보/결과 안내 링크 검사, 소개 자산/앵커 검사, TypeScript/Vite build 통과. 4개 보관 파일이 HEAD 원문/hash와 동일. backend/skills/prompts/configs/supabase/mcp_server/frontend/src와 평가 원본·후보 byte 불변 확인. 전체 기능 테스트는 실행 코드 변경이 없어 반복하지 않음.
미확인: 이 작업은 새 provider/실녹음/품질 평가를 수행하지 않음. commit/push/PR/merge/배포 미수행.
다음: 검토 가능한 diff에서 승인받은 범위만 GitHub 반영.

스크린샷 후속: README에 clone → 예제 복사·키 입력 → Compose 실행 절차와 검증 경계를 추가. .env.example의 Skill 표기를 활성 v6에 맞추고 STT 사전 다운로드를 비활성화했다. Compose 설정 문법 검사를 통과했다. main e6ecc4b 새 clone의 최초 설치는 GPU 의존성 다운로드와 image export 때문에 10분을 넘겨 약 616.6초에 검증을 중단했다. healthy/HTTP·실제 로그인/음성/코칭은 이번 검증에서 미확인. 상세: `docs/evidence/clean-compose-reproduction-20261010.md`. CPU 전용 의존성 고정과 재검증이 필요하다. 운영 배포 설정·실행 코드는 변경하지 않았다.

후속 승인: 사용자가 로컬 CPU 재현 구성과 함께 폴더 정리·README를 PR 생성 후 merge하도록 요청했다. 별도 [CPU Worklog](2026-10-10_local-cpu-reproduction.md)와 [최종 재현 결과](../evidence/local-cpu-reproduction-20261010.md)에 로컬 전용 이미지·STT 검증을 기록했다. 최초 10분 초과 기록은 실패 증거로 유지한다.
