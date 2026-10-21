from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from app.schemas.delivery import SpeechSegment


class SpeechSegmentDetector(Protocol):
    def detect(self, audio_path: Path) -> list[SpeechSegment]: ...


class SileroVadDetector:
    def __init__(
        self,
        model_loader: Callable[[], Any] | None = None,
        audio_reader: Callable[..., Any] | None = None,
        timestamp_getter: Callable[..., list[dict[str, float]]] | None = None,
        sampling_rate: int = 16_000,
    ) -> None:
        self._model_loader = model_loader or _load_model
        self._audio_reader = audio_reader or _decode_audio
        self._timestamp_getter = timestamp_getter or _get_speech_timestamps
        self._sampling_rate = sampling_rate
        self._model: Any | None = None

    def detect(self, audio_path: Path) -> list[SpeechSegment]:
        if self._model is None:
            self._model = self._model_loader()
        waveform = self._audio_reader(str(audio_path), sampling_rate=self._sampling_rate)
        timestamps = self._timestamp_getter(
            waveform,
            self._model,
            sampling_rate=self._sampling_rate,
            return_seconds=True,
        )
        return [
            SpeechSegment(round(float(item["start"]), 3), round(float(item["end"]), 3))
            for item in timestamps
        ]


def _load_model() -> Any:
    try:
        from silero_vad import load_silero_vad
    except ImportError as error:
        raise RuntimeError(
            "silero-vad가 설치되지 않았습니다. backend/requirements-stt.txt를 설치하세요."
        ) from error
    # Windows의 한글 경로에서도 PyTorch JIT 파일을 직접 열지 않도록 ONNX runtime을 사용한다.
    return load_silero_vad(onnx=True)


def _decode_audio(path: str, sampling_rate: int) -> Any:
    """Decode supported local audio without relying on torchaudio backend APIs."""
    import av
    import torch

    chunks: list[Any] = []
    with av.open(path) as container:
        if not container.streams.audio:
            raise ValueError("오디오 스트림을 찾을 수 없습니다.")
        resampler = av.audio.resampler.AudioResampler(
            format="flt", layout="mono", rate=sampling_rate
        )
        for frame in container.decode(container.streams.audio[0]):
            for resampled in resampler.resample(frame):
                chunks.append(torch.from_numpy(resampled.to_ndarray().reshape(-1)))
        for resampled in resampler.resample(None):
            chunks.append(torch.from_numpy(resampled.to_ndarray().reshape(-1)))

    if not chunks:
        raise ValueError("오디오 데이터를 읽을 수 없습니다.")
    return torch.cat(chunks).to(dtype=torch.float32)


def _get_speech_timestamps(
    waveform: Any,
    model: Any,
    sampling_rate: int,
    return_seconds: bool,
) -> list[dict[str, float]]:
    from silero_vad import get_speech_timestamps

    return get_speech_timestamps(
        waveform,
        model,
        sampling_rate=sampling_rate,
        return_seconds=return_seconds,
    )
