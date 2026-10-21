import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from app.schemas.stt import FillerAnalysis, SegmentTranscript, SttResult, WordTiming
from app.services.remote_stt import RemoteSttTranscriber
from app.services.stt_transcriber import FasterWhisperTranscriber


class RemoteSttTest(unittest.TestCase):
    def setUp(self):
        self.remote = RemoteSttTranscriber("https://stt-test.a.run.app")
        self.word = WordTiming("지가", 0.0, 0.5, 0.9)
        self.result = SttResult(
            "answer-1", "/opt/models/malhaebom-c2", "cuda", "float16", "ko", 1.0,
            2.0, 0.3, 0.15, "지가 그래가 했습니다.",
            FillerAnalysis({"음": 0}, 0, {"음": []}),
            [SegmentTranscript(0.0, 2.0, "지가 그래가 했습니다.", [self.word])],
            [self.word],
        )

    def response(self, status=200, payload=None):
        return httpx.Response(
            status, json=payload or self.result.to_dict(),
            request=httpx.Request("POST", self.remote.url + "/transcribe"),
        )

    def test_preserves_dialect_and_nested_timings_and_passes_hints(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.webm"
            audio.write_bytes(b"audio-bytes")
            with patch.object(self.remote, "_headers", return_value={"Authorization": "Bearer test"}), patch("app.services.remote_stt.httpx.post", return_value=self.response()) as post:
                result = self.remote.transcribe(audio, "answer-1", initial_prompt=" Redis, 캐시 ")
                self.assertEqual(post.call_args.kwargs["data"], {"source_id": "answer-1", "initial_prompt": "Redis, 캐시"})
                self.assertEqual(post.call_args.kwargs["files"]["audio"][0], "answer.webm")
        self.assertEqual(result.to_dict(), self.result.to_dict())

    def test_rejects_cpu_fallback_or_wrong_source(self):
        for key, value in (("device", "cpu"), ("source_id", "other-answer"), ("compute_type", "int8")):
            payload = self.result.to_dict()
            payload[key] = value
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                audio = Path(directory) / "answer.wav"
                audio.write_bytes(b"audio")
                with patch.object(self.remote, "_headers", return_value={}), patch("app.services.remote_stt.httpx.post", return_value=self.response(payload=payload)):
                    with self.assertRaises(RuntimeError):
                        self.remote.transcribe(audio, "answer-1")

    def test_upstream_failure_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "answer.wav"
            audio.write_bytes(b"audio")
            with patch.object(self.remote, "_headers", return_value={}), patch("app.services.remote_stt.httpx.post", return_value=self.response(status=503)):
                with self.assertRaises(httpx.HTTPStatusError):
                    self.remote.transcribe(audio, "answer-1")

    def test_metadata_token_has_worker_audience(self):
        token = httpx.Response(200, text="test-token", request=httpx.Request("GET", "http://metadata.google.internal"))
        with patch("app.services.remote_stt.httpx.get", return_value=token) as get:
            headers = self.remote._headers()
        self.assertIn("audience=https%3A%2F%2Fstt-test.a.run.app", get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs["headers"], {"Metadata-Flavor": "Google"})
        self.assertFalse(get.call_args.kwargs["trust_env"])
        self.assertEqual(headers, {"Authorization": "Bearer test-token"})

    def test_remote_dispatch_does_not_load_local_model(self):
        with patch.dict(os.environ, {"STT_REMOTE_URL": self.remote.url}), patch("app.services.remote_stt.RemoteSttTranscriber.transcribe", return_value=self.result) as call, patch("app.services.stt_transcriber.FasterWhisperTranscriber._default_model_factory") as factory:
            service = FasterWhisperTranscriber()
            with tempfile.TemporaryDirectory() as directory:
                audio = Path(directory) / "answer.wav"
                audio.write_bytes(b"audio")
                self.assertEqual(service.transcribe(audio, "answer-1"), self.result)
            self.assertEqual(call.call_count, 1)
            factory.assert_not_called()
