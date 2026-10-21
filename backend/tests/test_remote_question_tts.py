from __future__ import annotations

import base64
import io
import json
import sys
import threading
import unittest
import wave
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.question_tts import QuestionTtsUnavailableError  # noqa: E402
from app.services.remote_question_tts import RemoteQuestionTtsSynthesizer  # noqa: E402


def make_wav() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24_000)
        audio.writeframes(b"\x01\x00" * 2_400)
    return output.getvalue()


class FakeWorkerClient:
    def __init__(self, *, ready: bool = True, events: list[dict] | None = None):
        self.ready = ready
        self.events = events or []
        self.requests: list[str] = []

    def is_ready(self) -> bool:
        return self.ready

    def synthesize(self, text: str) -> bytes:
        self.requests.append(text)
        return make_wav()

    def synthesize_pcm_stream(self, text: str):
        self.requests.append(text)
        payload = b"".join(
            json.dumps(event).encode("utf-8") + b"\n" for event in self.events
        )
        midpoint = len(payload) // 2
        yield payload[:midpoint]
        yield payload[midpoint:]


class RemoteQuestionTtsSynthesizerTest(unittest.TestCase):
    def test_synthesizes_valid_wav_and_adds_question_suffix(self):
        client = FakeWorkerClient()
        result = RemoteQuestionTtsSynthesizer(client).synthesize("질문입니다.")

        self.assertEqual(result.duration_ms, 100)
        self.assertEqual(client.requests, ["질문입니다.//"])

    def test_converts_worker_events_to_final_pcm_chunks(self):
        first = b"\x01\x00" * 10
        second = b"\x02\x00" * 10
        client = FakeWorkerClient(
            events=[
                {
                    "type": "start",
                    "text": "질문입니다.//",
                    "format": "pcm_s16le",
                    "sampleRate": 24_000,
                    "channels": 1,
                },
                {
                    "type": "audio",
                    "sequence": 0,
                    "pcmBase64": base64.b64encode(first).decode("ascii"),
                },
                {
                    "type": "audio",
                    "sequence": 1,
                    "pcmBase64": base64.b64encode(second).decode("ascii"),
                },
                {"type": "complete"},
            ]
        )

        chunks = list(
            RemoteQuestionTtsSynthesizer(client).stream(
                "질문입니다.//",
                threading.Event(),
            )
        )

        self.assertEqual([item.pcm16 for item in chunks], [first, second])
        self.assertEqual([item.is_final for item in chunks], [False, True])

    def test_rejects_invalid_worker_sequence(self):
        client = FakeWorkerClient(
            events=[
                {
                    "type": "start",
                    "text": "질문",
                    "format": "pcm_s16le",
                    "sampleRate": 24_000,
                    "channels": 1,
                },
                {
                    "type": "audio",
                    "sequence": 2,
                    "pcmBase64": base64.b64encode(b"\x01\x00").decode("ascii"),
                },
            ]
        )

        with self.assertRaises(QuestionTtsUnavailableError):
            list(
                RemoteQuestionTtsSynthesizer(client).stream(
                    "질문//",
                    threading.Event(),
                )
            )

    def test_warmup_requires_ready_worker(self):
        with self.assertRaises(QuestionTtsUnavailableError):
            RemoteQuestionTtsSynthesizer(
                FakeWorkerClient(ready=False)
            ).warmup()


if __name__ == "__main__":
    unittest.main()
