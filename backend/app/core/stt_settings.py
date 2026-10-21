from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SttSettings:
    model_name: str = "large-v3-turbo"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 1

    @classmethod
    def from_env(cls) -> "SttSettings":
        beam_size = int(os.getenv("STT_BEAM_SIZE", "1"))
        if beam_size < 1:
            raise ValueError("STT_BEAM_SIZE는 1 이상이어야 합니다.")

        device = os.getenv("STT_DEVICE", "cpu").strip().lower()
        if device not in {"cpu", "cuda"}:
            raise ValueError("STT_DEVICE는 cpu 또는 cuda여야 합니다.")

        return cls(
            model_name=os.getenv("STT_MODEL_NAME", "large-v3-turbo").strip(),
            device=device,
            compute_type=os.getenv("STT_COMPUTE_TYPE", "int8").strip(),
            beam_size=beam_size,
        )
