#!/usr/bin/env python3
"""Run C1/C2 AI Hub 71592 continuation experiments sequentially."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venvs/stt-train/bin/python"
TRAINER = ROOT / "backend/scripts/train_whisper_qlora.py"
CONFIGS = [
    ROOT / "configs/stt/finetune_71592_only_5070ti.json",
    ROOT / "configs/stt/finetune_71592_replay20_5070ti.json",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--preflight-only", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not PYTHON.is_file():
        raise FileNotFoundError(PYTHON)
    for config in CONFIGS:
        spec = json.loads(config.read_text(encoding="utf-8"))
        output_dir = ROOT / spec["output_dir"]
        completed_adapter = output_dir / "best_adapter" / "adapter_model.safetensors"
        if completed_adapter.is_file() and not args.preflight_only:
            print(f"[skip] completed: {config.name}", flush=True)
            continue
        argv = [
            str(PYTHON),
            str(TRAINER),
            "--config",
            str(config),
        ]
        if args.preflight_only:
            argv.append("--preflight-only")
        print("+ " + " ".join(argv), flush=True)
        subprocess.run(argv, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
