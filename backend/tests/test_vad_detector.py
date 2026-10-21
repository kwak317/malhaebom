from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.delivery import SpeechSegment
from app.services.vad_detector import SileroVadDetector


class SileroVadDetectorTest(unittest.TestCase):
    def test_detect_converts_timestamps_and_loads_model_once(self) -> None:
        loader = Mock(return_value=object())
        detector = SileroVadDetector(
            model_loader=loader,
            audio_reader=lambda _, sampling_rate: object(),
            timestamp_getter=lambda *_args, **_kwargs: [{"start": 0.1234, "end": 1.9876}],
        )

        first = detector.detect(Path("answer.wav"))
        second = detector.detect(Path("answer.wav"))

        self.assertEqual([SpeechSegment(0.123, 1.988)], first)
        self.assertEqual(first, second)
        loader.assert_called_once()

    def test_detect_returns_empty_list_for_no_speech(self) -> None:
        detector = SileroVadDetector(
            model_loader=lambda: object(),
            audio_reader=lambda _, sampling_rate: object(),
            timestamp_getter=lambda *_args, **_kwargs: [],
        )

        self.assertEqual([], detector.detect(Path("silent.wav")))


if __name__ == "__main__":
    unittest.main()
