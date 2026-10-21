#!/usr/bin/env python3
"""Convert C1/C2 adapters and run B0/C1/C2 historical-retention CT2 evaluation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "backend/scripts/prepare_stt_eval_manifest.py"
CONVERTER = ROOT / "backend/scripts/convert_stt_retrain_to_ct2.py"
EVALUATOR = ROOT / "backend/scripts/evaluate_stt_ct2.py"
COMPARE = ROOT / "backend/scripts/compare_stt_71592_retention.py"

CONVERT_PYTHON = ROOT / ".venv/bin/python"
CT2_CONVERTER = ROOT / ".venvs/stt-runtime/bin/ct2-transformers-converter"
RUNTIME_PYTHON = ROOT / ".venvs/stt-runtime/bin/python"

SOURCE_MANIFEST = (
    ROOT / "data/stt/aihub71592-domain-20260922/retention-validation.jsonl"
)
EVAL_DIR = ROOT / "data/stt/71592-retention-validation"
OUTPUT_ROOT = ROOT / "artifacts/stt/71592-retention"
MODEL_ROOT = ROOT / "artifacts/stt/71592-retention-models"

B0 = (
    ROOT
    / "artifacts/stt/whisper-medium-busan-qlora-clean-cont-lr2e-5-ct2"
)
CANDIDATES = {
    "c1-71592-only": (
        ROOT / "artifacts/stt/whisper-medium-71592-only-lr1e-5/best_adapter"
    ),
    "c2-71592-replay20": (
        ROOT / "artifacts/stt/whisper-medium-71592-replay20-lr1e-5/best_adapter"
    ),
}
EXPECTED_ROWS = 4802


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--keep-merged", action="store_true")
    return p.parse_args()


def run(argv: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(argv), flush=True)
    subprocess.run(argv, cwd=ROOT, env=env, check=True)


def required_ct2(model: Path) -> list[Path]:
    return [
        model / "config.json",
        model / "model.bin",
        model / "tokenizer.json",
        model / "vocabulary.json",
        model / "preprocessor_config.json",
    ]


def ct2_complete(model: Path) -> bool:
    return all(path.is_file() for path in required_ct2(model))


def runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    lib_dirs: list[str] = []
    site_root = ROOT / ".venvs/stt-train/lib"
    for py_dir in sorted(site_root.glob("python3.*")):
        for rel in (
            "site-packages/nvidia/cublas/lib",
            "site-packages/nvidia/cudnn/lib",
        ):
            candidate = py_dir / rel
            if candidate.is_dir():
                lib_dirs.append(str(candidate))
    existing = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = ":".join(
        [*lib_dirs, *([existing] if existing else [])]
    )
    return env


def prepare_manifest() -> None:
    run(
        [
            sys.executable,
            str(PREPARE),
            "--input",
            str(SOURCE_MANIFEST),
            "--output-dir",
            str(EVAL_DIR),
            "--name",
            "71592-historical-retention-validation",
            "--overwrite",
        ]
    )


def validate() -> None:
    if not SOURCE_MANIFEST.is_file():
        raise FileNotFoundError(SOURCE_MANIFEST)
    for required in (CONVERT_PYTHON, CT2_CONVERTER, RUNTIME_PYTHON):
        if not required.is_file():
            raise FileNotFoundError(required)
    if not ct2_complete(B0):
        raise FileNotFoundError(f"incomplete B0 CT2 model: {B0}")
    for name, adapter in CANDIDATES.items():
        weight = adapter / "adapter_model.safetensors"
        if not weight.is_file():
            raise FileNotFoundError(f"{name}: {weight}")

    manifest = EVAL_DIR / "manifest.jsonl"
    rows = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(
            f"retention rows {len(rows)} != expected {EXPECTED_ROWS}"
        )
    missing = [
        row["audio"]
        for row in rows
        if not (EVAL_DIR / row["audio"]).resolve().is_file()
    ]
    if missing:
        raise FileNotFoundError(f"missing eval audio: {missing[0]}")

    free_gib = shutil.disk_usage(ROOT).free / 1024**3
    if free_gib < 10:
        raise RuntimeError(
            f"insufficient free disk for sequential CT2 conversion: {free_gib:.1f} GiB"
        )

    print(
        json.dumps(
            {
                "retention_rows": len(rows),
                "free_disk_gib": round(free_gib, 1),
                "b0_ct2": str(B0),
                "candidate_adapters": {
                    name: str(path) for name, path in CANDIDATES.items()
                },
                "runtime_python": str(RUNTIME_PYTHON),
                "convert_python": str(CONVERT_PYTHON),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("71592 retention preflight PASSED")


def convert_candidates(keep_merged: bool) -> dict[str, Path]:
    models = {"b0-clean": B0}
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    for name, adapter in CANDIDATES.items():
        merged = MODEL_ROOT / f"{name}-merged-hf"
        ct2 = MODEL_ROOT / f"{name}-ct2"
        models[name] = ct2
        if ct2_complete(ct2):
            print(f"[skip] {name}: CT2 model already complete", flush=True)
            continue
        run(
            [
                str(CONVERT_PYTHON),
                str(CONVERTER),
                "--adapter-dir",
                str(adapter),
                "--merged-dir",
                str(merged),
                "--ct2-dir",
                str(ct2),
            ]
        )
        if not ct2_complete(ct2):
            raise RuntimeError(f"{name}: CT2 conversion incomplete")
        if merged.exists() and not keep_merged:
            shutil.rmtree(merged)
            print(f"[cleanup] removed merged HF directory: {merged}", flush=True)
    return models


def metrics_complete(path: Path, model: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        data.get("utterances") == EXPECTED_ROWS
        and data.get("start_index") == 0
        and data.get("beam_size") == 5
        and data.get("compute_type") == "float16"
        and Path(str(data.get("model", ""))).resolve() == model.resolve()
        and Path(str(data.get("eval_dir", ""))).resolve()
        == EVAL_DIR.resolve()
    )


def evaluate(models: dict[str, Path]) -> None:
    env = runtime_env()
    for name, model in models.items():
        output = OUTPUT_ROOT / name
        metrics = output / "metrics.json"
        if metrics_complete(metrics, model):
            print(f"[skip] {name}: complete retention metrics already exist")
            continue
        run(
            [
                str(RUNTIME_PYTHON),
                str(EVALUATOR),
                "--model",
                str(model),
                "--eval-dir",
                str(EVAL_DIR),
                "--output-dir",
                str(output),
            ],
            env=env,
        )


def main() -> int:
    args = parse_args()
    prepare_manifest()
    validate()
    if args.preflight_only:
        return 0

    models = convert_candidates(args.keep_merged)
    evaluate(models)
    run([sys.executable, str(COMPARE)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
