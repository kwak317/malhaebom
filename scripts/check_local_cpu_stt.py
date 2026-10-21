"""Run real local CPU STT/VAD on an explicitly supplied test audio file.

No provider/auth/DB calls are made. This is a runtime smoke check, not an
accuracy benchmark or an authenticated browser test.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    args = parser.parse_args()

    import torch
    from app.core.stt_settings import SttSettings
    from app.services.stt_transcriber import FasterWhisperTranscriber
    from app.services.vad_detector import SileroVadDetector

    assert not os.getenv("STT_REMOTE_URL", "").strip(), "Remote STT is not a local CPU check"
    settings = SttSettings.from_env()
    assert settings.device == "cpu" and settings.compute_type == "int8"
    assert torch.version.cuda is None
    gpu_packages = sorted(
        d.metadata["Name"]
        for d in importlib.metadata.distributions()
        if d.metadata["Name"].lower().startswith(("nvidia-", "cuda-"))
    )
    assert not gpu_packages, gpu_packages
    started = time.perf_counter()
    result = FasterWhisperTranscriber(settings).transcribe(args.audio, "local-cpu-smoke")
    speech = SileroVadDetector().detect(args.audio)
    assert result.text.strip() and result.words and result.segments
    assert result.audio_duration_sec > 0 and speech
    assert all(0 <= word.start <= word.end for word in result.words)
    assert all(0 <= segment.start < segment.end for segment in speech)
    print(json.dumps({
        "model": result.model,
        "device": result.device,
        "compute_type": result.compute_type,
        "torch": torch.__version__,
        "torchaudio": importlib.metadata.version("torchaudio"),
        "cuda": torch.version.cuda,
        "gpu_packages": gpu_packages,
        "audio_duration_sec": result.audio_duration_sec,
        "stt_processing_time_sec": result.processing_time_sec,
        "total_with_model_load_and_vad_sec": round(time.perf_counter() - started, 3),
        "text": result.text,
        "words": len(result.words),
        "segments": len(result.segments),
        "speech_segments": len(speech),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
