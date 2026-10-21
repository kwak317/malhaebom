# Worklog — STT 파인튜닝 전·후 비교 리포트

- 일시: 2026-10-09
- 작업자: Codex
- 요구: Drive 자료와 첨부 비교 문서를 바탕으로 리포트 작성, 전·후 비교 필수, PR만 생성하고 merge하지 않음

## 1. 목적

파인튜닝 단계별 동일 평가셋의 CER/WER 변화와 개선·회귀를 구분한 리뷰 가능한 보고서를 작성한다.

## 2. 작업 전 상태

GitHub main fd9a6b9에 상세 계보 문서와 실험 기록이 이미 있었다. 중복 리포트를 만들지 않고 기존 docs/stt-finetuning-lineage.md를 canonical로 유지했다.

## 3. 수행 내용 및 주요 판단

- 첨부 「STT 파인튜닝 전·후 비교 분석」, Drive 인계 가이드·README·ARCHIVE-SHA256SUMS.txt를 읽고 저장소 실험·선택 JSON과 대조했다.
- 기존 6k와 현재 계보 요약, 단계별 전후 비교표, 지표 정의와 출처 확인 범위를 추가했다.
- 24건과 기술 질문의 수치를 발화형 정규화로 명시하고 24건 raw 결과도 추가했다.
- 전체 30건 WER, historical retention, 일반/장문/stress 구간의 악화를 함께 보존했다.
- 미학습 medium 및 기존 6k→C2의 동일 test 비교 미확보를 명시했다. final test와 Test B 점수를 직접 비교하지 않는다.

## 4. 변경 파일

- docs/stt-finetuning-lineage.md: 리포트 보강; 기존 개별 실험 링크 유지
- EVAL_REPORT.md: STT 리포트로 별도 연결; LLM 평가 수치 유지
- docs/CURRENT_STATE.md, docs/project2-checkpoint-work-cards.md: 확인 범위와 링크 추가, 상태 유지
- docs/worklogs/README.md와 이 기록

## 5. 검증

표의 전후 값은 단계별 원 실험에서 확인하고 변화값은 표시 수치 기준 Decimal 뺄셈으로 대조했다. 신규 로컬 문서 링크 존재 여부, C2 frozen selection과 step 480, git diff --check 및 PR review-size 정책을 확인했다. 문서 변경이므로 모델 재학습이나 애플리케이션 테스트는 수행하지 않았다.

## 6. 발견한 문제 / 미확인 사항

- 첨부와 기존 계보 문서 일부는 raw/발화형 정규화 구분이 불명확해 원 실험 기준으로 보완했다.
- Google Docs 가이드는 Markdown export로 읽었으며, 원래 Markdown 파일인 README의 GSuite export는 HTTP 500으로 실패해 보기 전용 문서 텍스트로 읽었다.
- Drive ZIP은 목록·게시 크기·체크섬 대조만 확인했다. 다운로드본 해시·내부 파일·모델 로드·새 추론은 미검증이다.
- 기존 평가를 재실행한 것이 아니며 speaker 독립성·다중 화자 acceptance·운영 채택은 여전히 별도 검증이 필요하다.

## 7. 다음 작업

PR을 OPEN 상태로 제공하고 merge하지 않는다. 모델 채택 판단은 새 독립 acceptance와 운영 runtime 평가 후 별도 진행한다.
