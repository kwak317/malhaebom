from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.services.question_tts import QuestionTtsUnavailableError


@dataclass(frozen=True)
class QuestionTtsSettings:
    model_path: Path

    @classmethod
    def from_env(cls) -> "QuestionTtsSettings":
        value = os.getenv("QUESTION_TTS_MODEL_PATH", "").strip()
        path = Path(value) if value else None
        if path is None or not path.is_dir():
            raise QuestionTtsUnavailableError()
        return cls(path)
