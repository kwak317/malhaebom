# 전달력 분석 계약 Spec

## Why

STT 전사문만으로는 말속도·긴 침묵·반복 표현을 일관되게 표시할 수 없다.

## Goal

VAD 발화 구간과 STT 결과를 받아 답변 시간, 실제 발화 시간, CPM, 긴 침묵, 반복 표현과 최대 두 개의 피드백을 표준 JSON으로 반환한다. VAD 모델 선택과 최종 임계값 확정은 범위 밖이다.

## What

정렬된 VAD 발화 구간을 병합하고, 발화 구간 사이의 1초 이상 공백만 긴 침묵으로 집계한다. 한글 음절 수와 실제 발화 시간으로 CPM을 계산하며, 인접한 같은 단어를 반복으로 기록한다. `SPEED_FAST`, `LONG_SILENCE`, `FILLER_REPEAT` 중 최대 두 개만 반환한다.

## How

`DeliveryAnalyzer.analyze(SttResult, list[SpeechSegment])`는 `DeliveryAnalysisResult`를 반환한다. 초기 임계값은 코드 주입값이며 실제 사용자 검증 전 확정 성능 수치가 아니다.

## AC

- Given 발화 구간 사이가 1초 이상일 때, When 분석하면, Then 긴 침묵의 시작·끝·길이를 반환한다.
- Given 실제 발화 시간이 0초일 때, When 분석하면, Then CPM은 `null`이다.
- Given 세 피드백 조건이 모두 충족될 때, When 분석하면, Then 우선순위 순서의 두 개만 반환한다.
