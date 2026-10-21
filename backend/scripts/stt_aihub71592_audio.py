#!/usr/bin/env python3
"""PCM16 WAV helpers for AI Hub 71592 segmentation."""

from __future__ import annotations

import io
import math
import wave
import zipfile
from pathlib import Path


def read_pcm16(
    zf: zipfile.ZipFile, member: str
) -> tuple[object, int]:
    import numpy as np

    raw = zf.read(member)
    with wave.open(io.BytesIO(raw), "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise ValueError(
                "expected mono PCM16 WAV, got "
                f"channels={wf.getnchannels()} "
                f"sample_width={wf.getsampwidth()}"
            )
        sample_rate = wf.getframerate()
        samples = np.frombuffer(
            wf.readframes(wf.getnframes()), dtype="<i2"
        ).copy()
    return samples, sample_rate


def write_clip(
    samples: object,
    sample_rate: int,
    start: float,
    end: float,
    path: Path,
) -> None:
    begin = max(0, int(math.floor(start * sample_rate)))
    finish = min(len(samples), int(math.ceil(end * sample_rate)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples[begin:finish].tobytes())
