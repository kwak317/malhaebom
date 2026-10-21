from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.delivery import SpeechSegment
from app.schemas.stt import FillerAnalysis, SegmentTranscript, SttResult, WordTiming
from app.services.delivery_analysis import DeliveryAnalyzer


def stt_result() -> SttResult:
    words = [WordTiming("저는", 0.0, 0.2, None), WordTiming("저는", 0.3, 0.5, None), WordTiming("음", 0.6, 0.7, None)]
    return SttResult("attempt-1", "large-v3-turbo", "cpu", "int8", "ko", None, 10.0, 0.2, 0.02, "저는 저는 음 개발자로 성장하고 싶습니다", FillerAnalysis({"음": 3, "어": 0}, 3, {"음": [], "어": []}), [], words)


class DeliveryAnalyzerTest(unittest.TestCase):
    def test_calculates_metrics_and_limits_feedback_to_two(self):
        result = DeliveryAnalyzer(fast_cpm=10).analyze(stt_result(), [SpeechSegment(0, 2), SpeechSegment(3.5, 6)])
        self.assertEqual(result.metrics.speech_duration_sec, 4.5)
        self.assertEqual(len(result.metrics.long_silences), 1)
        self.assertEqual(len(result.metrics.repetitions), 1)
        self.assertEqual([item.code for item in result.feedback], ["SPEED_FAST", "LONG_SILENCE"])

    def test_returns_null_cpm_when_vad_has_no_speech(self):
        result = DeliveryAnalyzer().analyze(stt_result(), [])
        self.assertIsNone(result.metrics.cpm)

    def test_detects_hedging_and_terminal_connective_endings(self):
        result = DeliveryAnalyzer().analyze(
            SttResult(
                "attempt-2", "large-v3-turbo", "cpu", "int8", "ko", None, 8.0, 0.2, 0.02,
                "백엔드를 담당했던 것 같습니다. 배포를 완료했고요.",
                FillerAnalysis({"음": 0, "어": 0}, 0, {"음": [], "어": []}),
                [
                    SegmentTranscript(0.0, 2.0, "백엔드를 담당했던 것 같습니다."),
                    SegmentTranscript(3.0, 4.0, "배포를 완료했고요."),
                ],
                [],
            ),
            [SpeechSegment(0, 2), SpeechSegment(3, 4)],
        )
        self.assertEqual([item.expression for item in result.metrics.soft_endings], ["것 같습니다", "완료했고요"])

    def test_does_not_flag_connective_ending_when_speech_immediately_continues(self):
        result = DeliveryAnalyzer().analyze(
            SttResult(
                "attempt-3", "large-v3-turbo", "cpu", "int8", "ko", None, 5.0, 0.2, 0.02,
                "배포를 완료했고요 이후 모니터링했습니다.",
                FillerAnalysis({"음": 0, "어": 0}, 0, {"음": [], "어": []}),
                [
                    SegmentTranscript(0.0, 1.0, "배포를 완료했고요"),
                    SegmentTranscript(1.3, 2.5, "이후 모니터링했습니다."),
                ],
                [],
            ),
            [SpeechSegment(0, 2.5)],
        )
        self.assertEqual(result.metrics.soft_endings, [])
