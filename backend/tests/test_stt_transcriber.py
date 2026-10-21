from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.stt_settings import SttSettings
from app.schemas.stt import WordTiming
from app.services.stt_transcriber import FasterWhisperTranscriber, analyze_fillers


class FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))
        words = [
            SimpleNamespace(word=" 음,", start=0.1, end=0.4, probability=0.91),
            SimpleNamespace(word="저는", start=0.5, end=0.8, probability=0.95),
            SimpleNamespace(word=" 어", start=0.9, end=1.2, probability=0.82),
            SimpleNamespace(word="개발자입니다.", start=1.3, end=2.0, probability=0.99),
        ]
        segments = [SimpleNamespace(start=0.0, end=2.0, text=" 음, 저는 어 개발자입니다.", words=words)]
        info = SimpleNamespace(duration=2.0, language="ko", language_probability=0.99)
        return iter(segments), info


class SttTranscriberTest(unittest.TestCase):
    def setUp(self):
        self.settings = SttSettings(
            model_name="large-v3-turbo", device="cpu", compute_type="int8", beam_size=1
        )

    def test_transcribe_returns_contract_without_local_path(self):
        fake = FakeModel()
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"not-decoded-by-fake")
            service = FasterWhisperTranscriber(
                settings=self.settings, model_factory=lambda _: fake
            )
            result = service.transcribe(audio, "attempt-123")

        payload = result.to_dict()
        self.assertEqual(payload["source_id"], "attempt-123")
        self.assertNotIn(str(audio), str(payload))
        self.assertEqual(payload["text"], "음, 저는 어 개발자입니다.")
        self.assertEqual(payload["fillers"]["counts"], {"음": 1, "어": 1})
        self.assertEqual(len(payload["words"]), 4)
        self.assertEqual(fake.calls[0][1]["beam_size"], 1)
        self.assertTrue(fake.calls[0][1]["word_timestamps"])
        self.assertFalse(fake.calls[0][1]["vad_filter"])

    def test_analyze_fillers_counts_only_exact_tokens(self):
        words = [
            WordTiming("음!", 0.0, 0.2, 0.9),
            WordTiming("어", 0.3, 0.5, 0.8),
            WordTiming("저는", 0.6, 0.9, 0.9),
            WordTiming("그", 1.0, 1.1, 0.9),
        ]
        result = analyze_fillers(words)
        self.assertEqual(result.counts, {"음": 1, "어": 1})
        self.assertEqual(result.total_count, 2)

    def test_transcribe_passes_trimmed_initial_prompt(self):
        fake = FakeModel()
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"not-decoded-by-fake")
            service = FasterWhisperTranscriber(
                settings=self.settings, model_factory=lambda _: fake
            )
            service.transcribe(
                audio,
                "attempt-123",
                initial_prompt="  기술 면접 답변입니다. Docker, FastAPI.  ",
            )

        self.assertEqual(
            fake.calls[0][1]["initial_prompt"],
            "기술 면접 답변입니다. Docker, FastAPI.",
        )

    def test_missing_file_does_not_load_model(self):
        called = False

        def factory(_):
            nonlocal called
            called = True
            return FakeModel()

        service = FasterWhisperTranscriber(self.settings, factory)
        with self.assertRaises(FileNotFoundError):
            service.transcribe("missing.wav", "attempt-123")
        self.assertFalse(called)

    def test_warmup_loads_the_model_once(self):
        calls = 0

        def factory(_):
            nonlocal calls
            calls += 1
            return FakeModel()

        service = FasterWhisperTranscriber(self.settings, factory)
        service.warmup()
        service.warmup()

        self.assertEqual(calls, 1)

    def test_unsupported_extension_does_not_load_model(self):
        called = False

        def factory(_):
            nonlocal called
            called = True
            return FakeModel()

        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.txt"
            audio.write_text("invalid", encoding="utf-8")
            service = FasterWhisperTranscriber(self.settings, factory)
            with self.assertRaises(ValueError):
                service.transcribe(audio, "attempt-123")
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
