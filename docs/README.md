# 문서 안내

## 현재 자료부터 찾기

| 목적 | 기준 문서 |
| --- | --- |
| 최신 구현·운영 | [CURRENT_STATE](CURRENT_STATE.md) · [README](../README.md) |
| 제출물·증거와 미확인 항목 | [SUBMISSION_EVIDENCE](SUBMISSION_EVIDENCE.md) · [평가 리포트](../EVAL_REPORT.md) |
| 구조·신뢰 경계 | [ARCHITECTURE](ARCHITECTURE.md) · [TRUST_BOUNDARY](TRUST_BOUNDARY.md) |
| 작업·실험 이력 | [Worklog 전체 인덱스](worklogs/INDEX.md) · [실험 안내](experiments/README.md) |
| 평가 원본·실험 후보 | [evals 안내](../evals/README.md) |
| 소개페이지 미리보기 출처 | [캡처 manifest](showcase/production-preview-manifest-20261010.json) |
| 사용하지 않는 과거 공개 자산 | [보관 안내](archive/README.md) |

파일명 날짜와 본문의 기준 commit/revision을 먼저 확인합니다. 과거 성공·후보·계획은 현재 운영 성공을 대신하지 않습니다. 기존 링크와 재현 스크립트를 위해 문서 원본 경로는 유지합니다.

## 분야별 상세 참고


현재 프로젝트 기준 문서는 [PROJECT_OVERVIEW](PROJECT_OVERVIEW.md) → [CURRENT_STATE](CURRENT_STATE.md) → [TARGET_STATE](TARGET_STATE.md) → [REQUIREMENTS](REQUIREMENTS.md) → [CONSTRAINTS](CONSTRAINTS.md) 순서로 읽습니다. 운영 규칙은 [AGENTS](../AGENTS.md), 현재/목표 구조는 [ARCHITECTURE](ARCHITECTURE.md)가 기준입니다.

이 저장소는 제품 범위와 데이터 경계, 현재 구현 계약을 함께 관리합니다. 아래 순서로 읽습니다.

1. [PRD](prd.md): MVP 흐름, 사용자 문제, 모델 비교·개인정보 원칙의 기준 문서입니다.
   - [제품 문제정의서](product/problem-definition.md): 사용자 문제와 MVP 검증 가설을 설명하는 보조 제품 문서입니다. 현재 구현·범위·계약의 canonical을 대체하지 않습니다.
   - [차별화 전략](product/differentiation-strategy.md): 현재 MVP의 포지셔닝과 구현된 공고 원문 분석·근거 검증 흐름의 표현 경계를 기록합니다.
   - [D7 중간 점검 1장](D7_INTERIM_CHECKPOINT_ONE_PAGE.md): 문제 정의·평가셋·아키텍처·baseline·제외 범위·남은 일정을 한 장으로 압축합니다.
2. [코칭 Skill 런타임 계약](specs/coaching-skill-runtime.md): `SKILL.md`, 문제 해결 질문 규칙, `criteria.json`의 단일 버전과 서버 검증 기준입니다.
3. [코칭 출력 계약](specs/coaching-output-contract.md): 여덟 개 응답 필드와 Pydantic·서버 검증 규칙입니다.
4. [코칭 평가·관측·E2E](specs/coaching-evaluation-ops.md): 30건 평가셋, 실패 상태, Langfuse 계약, Docker E2E와 모델 비교 기준입니다.
5. [저장소 구현 점검표](repository-audit.md): 현재 구현된 항목과 외부 결정이 필요한 보류 항목입니다.
6. [기능 Spec](specs/): 구현하려는 기능의 Why · Goal · What · How · AC를 확인합니다. 새 기능은 [예시](specs/_example.md)를 복사하지 말고 형식만 따라 새 파일로 작성합니다.
7. [GitHub 기술 증거 기반 공고 핏 진단 Spec](specs/github-evidence-job-fit.md): 공개 GitHub 프로젝트 근거와 선택 공고 요구를 대조해 답변 보완·심층 꼬리질문으로 연결하는 제안 기능의 경계입니다.
8. [경쟁 서비스 대비](competitor-comparison.md): 사람인 AI 모의면접의 공개 안내와 위 제안 기능의 차별화·표현 경계를 기록합니다.
9. [TTS 사전 생성 피드백 템플릿 Spec](specs/tts-사전생성-피드백템플릿.md): 기본 질문·고정 템플릿 코치 피드백의 검수 완료 WAV 재생 정책입니다.
10. [사용자 입력 면접 질문 TTS Spec](specs/custom-question-tts.md): 사용자가 직접 입력한 질문만 승인 모델로 실시간 합성하는 조건과 보관 규칙입니다.
11. [분석 결과 코치 피드백 TTS Spec](specs/coach-feedback-tts.md): 분석 LLM이 만든 짧은 피드백만 승인 모델로 실시간 합성하고, 연습 기록용 WAV·텍스트를 최대 24시간 보관하는 조건입니다.
12. [TTS 현재 상태](tts-current-status.md): 로컬 검수 후보, 현재 텍스트 폴백 상태, 앱 연결 전 조건입니다.
13. [TTS 자산 인수인계](tts-asset-handoff.md): 검수된 사전 생성 WAV를 비공개 자산으로 연결하는 역할·안전 조건입니다.
14. [STT 현재 상태](stt-current-status.md): faster-whisper Worker와 Whisper-medium LoRA 파일럿의 확인된 범위·남은 평가 항목입니다.
15. [STT 파인튜닝 계보와 면접 도메인 적응](stt-finetuning-lineage.md): legacy 6k LoRA, 50k QLoRA retrain, clean continuation, AI Hub 71592 replay20까지의 학습 계보와 평가 근거를 정리합니다.
16. [Python 환경 재현 기준](PYTHON_ENVIRONMENT.md): 최신 STT/TTS handoff와 원 전달 번들을 함께 사용한 runtime/train 환경의 source-of-truth와 설치·검증 방법입니다.
17. [AI Hub STT 119 데이터 준비 및 재구성](AIHUB_DATA_DOWNLOAD.md): 최신 STT handoff 50,000/5,000 manifest를 AI Hub 경상도 원천 archive에서 검증·재구성하는 절차입니다.
18. [STT 공개 모델 다운로드](STT_MODEL_DOWNLOAD.md): AI Hub 원본·전사·평가 음성을 제외한 공개 가능 추론 모델을 gdown으로 내려받고 checksum을 검증하는 절차입니다.
19. [TTS 공개 모델 다운로드](TTS_MODEL_DOWNLOAD.md): 질문자·코치 Qwen3-TTS 계열 모델을 gdown으로 내려받고 size/SHA-256을 검증하는 절차입니다.
20. [추적 파일·Git 제외 규칙 점검](evidence/2026-10-01-tracked-artifact-audit.md): 민감 파일명 및 생성 산출물의 추적 여부, 제외 규칙 검사 결과와 한계를 기록합니다.

## 문서와 로컬 실험의 경계

실험 기록의 절대경로는 당시 환경에만 유효한 참고 정보이며, 저장소를 clone한 팀원의 실행 경로가 아닙니다. 현재 실행 명령은 저장소 상대경로를 사용하고, 환경별 외부 자산 위치는 Git에서 제외한 로컬 설정으로 지정합니다.

공유가 필요한 것은 비민감한 Spec, 평가 지표, 청취 판정, 템플릿 ID와 검수 상태입니다. 음성·모델·비밀 값은 `.gitignore` 대상이며 PR에도 첨부하지 않습니다.

## 관측·사람 평가 증거

- [운영 Langfuse trace와 실제 코칭 응답 사람 평가](evidence/observability-human-evaluation-2026-10-06.md): 기존 기록, 서버 재조회 및 각 버전의 확인 범위.
