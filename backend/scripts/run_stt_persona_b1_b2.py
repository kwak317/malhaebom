#!/usr/bin/env python3
"""Run B1 new-only and B2 80:20 replay STT continuation sequentially."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venvs/stt-train/bin/python"
TRAIN = ROOT / "backend/scripts/train_whisper_qlora.py"
CONFIGS = [
    ROOT / "configs/stt/finetune_persona_new_only_5070ti.json",
    ROOT / "configs/stt/finetune_persona_replay20_5070ti.json",
]


def run(argv: list[str]) -> None:
    print("+ " + " ".join(argv), flush=True)
    subprocess.run(argv, cwd=ROOT, check=True)


def main() -> int:
    if not PYTHON.is_file():
        raise FileNotFoundError(PYTHON)
    for config in CONFIGS:
        run([str(PYTHON), str(TRAIN), "--config", str(config), "--preflight-only"])
    for config in CONFIGS:
        run([str(PYTHON), str(TRAIN), "--config", str(config)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
