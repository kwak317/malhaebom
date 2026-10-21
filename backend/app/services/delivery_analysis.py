from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from app.schemas.delivery import (
    DeliveryAnalysisResult,
    DeliveryMetrics,
    FeedbackItem,
    LongSilence,
    RepeatedExpression,
    SpeechSegment,
    SoftEnding,
)
from app.schemas.stt import SegmentTranscript, SttResult, WordTiming


ALLOWED_ISSUE_CODES = ("SPEED_FAST", "LONG_SILENCE", "FILLER_REPEAT", "SOFT_ENDING")
SOFT_ENDING_PATTERNS = (
    (
        re.compile(r"(?P<expression>(?:인\s*)?것\s*(?:같습니다|같아요|같고요))\s*[.!?…]*\s*$"),
        "사실에 근거한 내용이라면 ‘…입니다’ 또는 ‘…했습니다’처럼 마무리해 보세요.",
        False,
    ),
    (
        re.compile(r"(?P<expression>[가-힣]+(?:고요|는데요))\s*[.!?…]*\s*$"),
        "문장이 끝났다면 ‘…했습니다.’처럼 종결형으로 마무리해 보세요.",
        True,
    ),
)


class DeliveryAnalyzer:
    """Converts STT output plus externally detected VAD speech segments into a stable contract."""

    def __init__(
        self,
        fast_cpm: float = 330.0,
        long_silence_sec: float = 1.0,
        filler_repeat_count: int = 3,
    ) -> None:
        self.fast_cpm = fast_cpm
        self.long_silence_sec = long_silence_sec
        self.filler_repeat_count = filler_repeat_count

    def analyze(
        self, stt: SttResult, vad_segments: Iterable[SpeechSegment]
    ) -> DeliveryAnalysisResult:
        segments = self._merge_segments(vad_segments)
        speech_duration = round(sum(item.end - item.start for item in segments), 3)
        syllables = sum("가" <= char <= "힣" for char in stt.text)
        cpm = round(syllables / speech_duration * 60, 1) if speech_duration else None
        long_silences = self._long_silences(segments)
        repetitions = self._repetitions(stt.words)
        soft_endings = self._soft_endings(stt.segments)
        metrics = DeliveryMetrics(
            answer_duration_sec=stt.audio_duration_sec,
            speech_duration_sec=speech_duration,
            cpm=cpm,
            long_silences=long_silences,
            repetitions=repetitions,
            soft_endings=soft_endings,
        )
        return DeliveryAnalysisResult(
            source_id=stt.source_id,
            metrics=metrics,
            feedback=self._feedback(stt, metrics),
        )

    def _merge_segments(self, segments: Iterable[SpeechSegment]) -> list[SpeechSegment]:
        merged: list[SpeechSegment] = []
        for segment in sorted(segments, key=lambda item: item.start):
            if segment.end <= segment.start:
                continue
            if merged and segment.start <= merged[-1].end:
                previous = merged[-1]
                merged[-1] = SpeechSegment(previous.start, max(previous.end, segment.end))
            else:
                merged.append(segment)
        return merged

    def _long_silences(self, segments: list[SpeechSegment]) -> list[LongSilence]:
        silences: list[LongSilence] = []
        for left, right in zip(segments, segments[1:]):
            duration = round(right.start - left.end, 3)
            if duration >= self.long_silence_sec:
                silences.append(LongSilence(left.end, right.start, duration))
        return silences

    @staticmethod
    def _repetitions(words: list[WordTiming]) -> list[RepeatedExpression]:
        repetitions: list[RepeatedExpression] = []
        previous: WordTiming | None = None
        for word in words:
            normalized = re.sub(r"[^가-힣a-z0-9]", "", unicodedata.normalize("NFKC", word.word).lower())
            if normalized and previous is not None:
                before = re.sub(r"[^가-힣a-z0-9]", "", unicodedata.normalize("NFKC", previous.word).lower())
                if normalized == before:
                    repetitions.append(RepeatedExpression(normalized, previous.start, word.start))
            previous = word
        return repetitions

    @staticmethod
    def _soft_endings(segments: list[SegmentTranscript]) -> list[SoftEnding]:
        endings: list[SoftEnding] = []
        for index, segment in enumerate(segments):
            text = unicodedata.normalize("NFKC", segment.text).strip()
            if not text:
                continue
            for pattern, suggestion, requires_pause in SOFT_ENDING_PATTERNS:
                match = pattern.search(text)
                if match is None:
                    continue
                if requires_pause and not DeliveryAnalyzer._is_terminal_segment(index, segments):
                    continue
                expression = re.sub(r"\s+", " ", match.group("expression")).strip()
                endings.append(SoftEnding(expression, segment.start, segment.end, suggestion))
                break
        return endings

    @staticmethod
    def _is_terminal_segment(index: int, segments: list[SegmentTranscript]) -> bool:
        if index == len(segments) - 1:
            return True
        return segments[index + 1].start - segments[index].end >= 0.7

    def _feedback(self, stt: SttResult, metrics: DeliveryMetrics) -> list[FeedbackItem]:
        candidates: list[FeedbackItem] = []
        if metrics.cpm is not None and metrics.cpm > self.fast_cpm:
            candidates.append(FeedbackItem("SPEED_FAST", f"말속도 {metrics.cpm} CPM", "한 문장씩 천천히 말해 보세요."))
        if metrics.long_silences:
            candidates.append(FeedbackItem("LONG_SILENCE", f"1초 이상 긴 침묵 {len(metrics.long_silences)}회", "다음 문장을 떠올린 뒤 이어서 말해 보세요."))
        if stt.fillers.total_count >= self.filler_repeat_count or metrics.repetitions:
            candidates.append(FeedbackItem("FILLER_REPEAT", f"추임새 {stt.fillers.total_count}회, 반복 표현 {len(metrics.repetitions)}회", "추임새를 줄이고 핵심어부터 말해 보세요."))
        if metrics.soft_endings:
            candidates.append(FeedbackItem("SOFT_ENDING", f"완곡한 문장 마무리 {len(metrics.soft_endings)}회", "사실에 근거한 경험은 더 단정한 종결형으로 마무리해 보세요."))
        return candidates[:2]
