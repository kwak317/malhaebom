#!/usr/bin/env python3
"""Merge a Whisper LoRA adapter and convert it to CTranslate2 float16."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import torch
from peft import PeftModel
from transformers import WhisperForConditionalGeneration, WhisperProcessor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_MODEL = "openai/whisper-medium"
DEFAULT_ADAPTER_DIR = (
    PROJECT_ROOT
    / "artifacts/stt/whisper-medium-busan-qlora-retrain/best_adapter"
)
DEFAULT_MERGED_DIR = (
    PROJECT_ROOT
    / "artifacts/stt/whisper-medium-busan-qlora-retrain-merged-hf"
)
DEFAULT_CT2_DIR = (
    PROJECT_ROOT
    / "[REDACTED]"
)
CONVERTER = PROJECT_ROOT / ".venv/bin/ct2-transformers-converter"


def project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default=BASE_MODEL)
    parser.add_argument("--adapter-dir", type=Path, default=DEFAULT_ADAPTER_DIR)
    parser.add_argument("--merged-dir", type=Path, default=DEFAULT_MERGED_DIR)
    parser.add_argument("--ct2-dir", type=Path, default=DEFAULT_CT2_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    adapter_dir = project_path(args.adapter_dir)
    merged_dir = project_path(args.merged_dir)
    ct2_dir = project_path(args.ct2_dir)

    if not (adapter_dir / "adapter_model.safetensors").is_file():
        raise FileNotFoundError(f"missing adapter weight: {adapter_dir}")
    if not CONVERTER.is_file():
        raise FileNotFoundError(f"missing converter: {CONVERTER}")

    print(f"[merge] base={args.base_model}")
    print(f"[merge] adapter={adapter_dir}")
    base = WhisperForConditionalGeneration.from_pretrained(
        args.base_model,
        dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    model = PeftModel.from_pretrained(base, adapter_dir)
    merged = model.merge_and_unload()

    if merged_dir.exists():
        shutil.rmtree(merged_dir)
    merged_dir.mkdir(parents=True)
    merged.save_pretrained(merged_dir, safe_serialization=True)

    processor = WhisperProcessor.from_pretrained(args.base_model)
    processor.save_pretrained(merged_dir)
    del model, base, merged
    print(f"[merge] saved={merged_dir}")

    if ct2_dir.exists():
        shutil.rmtree(ct2_dir)

    cmd = [
        str(CONVERTER),
        "--model",
        str(merged_dir),
        "--output_dir",
        str(ct2_dir),
        "--quantization",
        "float16",
        "--copy_files",
        "tokenizer.json",
        "preprocessor_config.json",
        "--force",
    ]
    print("[ct2] " + " ".join(cmd))
    subprocess.run(cmd, check=True)

    required = [
        ct2_dir / "config.json",
        ct2_dir / "model.bin",
        ct2_dir / "tokenizer.json",
        ct2_dir / "vocabulary.json",
        ct2_dir / "preprocessor_config.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"CT2 conversion missing expected files: {missing}")

    print(
        json.dumps(
            {
                "adapter_dir": str(adapter_dir),
                "merged_dir": str(merged_dir),
                "ct2_dir": str(ct2_dir),
                "ct2_files": {
                    path.name: path.stat().st_size for path in required
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
