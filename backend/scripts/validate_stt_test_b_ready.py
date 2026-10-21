#!/usr/bin/env python3
"""Validate all artifacts required for the fixed STT Test B three-way comparison."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_B = ROOT / "data/stt/holdout-test-b-clean"
MODELS = {
    "baseline": ROOT / "[REDACTED]",
    "retrain": ROOT / "[REDACTED]",
    "clean_continuation": ROOT
    / "[REDACTED]",
}
REQUIRED_CT2 = (
    "config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.json",
    "preprocessor_config.json",
)
PLACEHOLDER_RE = re.compile(r"#.+?#|&[^&]+&")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = TEST_B / "manifest.jsonl"
    metadata = TEST_B / "metadata.json"
    if not manifest.is_file() or not metadata.is_file():
        raise FileNotFoundError(f"Test B is incomplete: {TEST_B}")

    rows = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 500:
        raise RuntimeError(f"expected 500 Test B rows, found {len(rows)}")
    if any(PLACEHOLDER_RE.search(str(row["reference"])) for row in rows):
        raise RuntimeError("Test B contains a placeholder reference")
    missing_audio = [
        str(TEST_B / row["audio"])
        for row in rows
        if not (TEST_B / row["audio"]).is_file()
    ]
    if missing_audio:
        raise FileNotFoundError(
            f"Test B missing {len(missing_audio)} audio files; first={missing_audio[0]}"
        )

    model_summary = {}
    compatibility_hashes: dict[str, dict[str, str]] = {}
    for name, model_dir in MODELS.items():
        missing = [
            filename
            for filename in REQUIRED_CT2
            if not (model_dir / filename).is_file()
        ]
        if missing:
            raise FileNotFoundError(f"{name} CT2 incomplete at {model_dir}: {missing}")
        model_summary[name] = {
            "path": str(model_dir),
            "model_bin_bytes": (model_dir / "model.bin").stat().st_size,
        }
        compatibility_hashes[name] = {
            filename: sha256(model_dir / filename)
            for filename in ("config.json", "tokenizer.json", "vocabulary.json")
        }

    baseline_hashes = compatibility_hashes["baseline"]
    for name, hashes in compatibility_hashes.items():
        if hashes != baseline_hashes:
            raise RuntimeError(
                f"{name}: CT2 config/tokenizer/vocabulary hashes differ from baseline"
            )

    result = {
        "test_b": str(TEST_B),
        "utterances": len(rows),
        "sources": len({row["source_id"] for row in rows}),
        "placeholder_references": 0,
        "models": model_summary,
        "shared_ct2_metadata_sha256": baseline_hashes,
        "decoding": {
            "beam_size": 5,
            "compute_type": "float16",
            "language": "ko",
            "task": "transcribe",
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "vad_filter": False,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
