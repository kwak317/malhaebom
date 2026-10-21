#!/usr/bin/env python3
"""Aggregate five fixed 100-sample candidate STT evaluation chunks."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNK_ROOT = PROJECT_ROOT / "artifacts/stt/candidate-holdout-chunks"
OUTPUT_DIR = PROJECT_ROOT / "artifacts/stt/candidate-holdout"
STARTS = [0, 100, 200, 300, 400]


def main() -> int:
    metrics_list = []
    predictions = []
    for start in STARTS:
        chunk = CHUNK_ROOT / str(start)
        metrics_path = chunk / "metrics.json"
        predictions_path = chunk / "predictions.json"
        if not metrics_path.is_file() or not predictions_path.is_file():
            raise FileNotFoundError(f"missing chunk output: {chunk}")
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if metrics.get("start_index") != start:
            raise RuntimeError(
                f"chunk {start}: unexpected start_index={metrics.get('start_index')}"
            )
        if metrics.get("utterances") != 100:
            raise RuntimeError(
                f"chunk {start}: unexpected utterances={metrics.get('utterances')}"
            )
        metrics_list.append(metrics)
        predictions.extend(
            json.loads(predictions_path.read_text(encoding="utf-8"))
        )

    first = metrics_list[0]
    for metrics in metrics_list[1:]:
        for key in ("beam_size", "compute_type", "model", "eval_dir"):
            if metrics.get(key) != first.get(key):
                raise RuntimeError(
                    f"incompatible chunk condition for {key}: "
                    f"{metrics.get(key)!r} != {first.get(key)!r}"
                )

    cer_edits = sum(int(m["cer_edits"]) for m in metrics_list)
    cer_units = sum(int(m["cer_units"]) for m in metrics_list)
    wer_edits = sum(int(m["wer_edits"]) for m in metrics_list)
    wer_units = sum(int(m["wer_units"]) for m in metrics_list)
    utterances = sum(int(m["utterances"]) for m in metrics_list)

    result = {
        "cer_percent": cer_edits / cer_units * 100 if cer_units else 0.0,
        "wer_percent": wer_edits / wer_units * 100 if wer_units else 0.0,
        "cer_edits": cer_edits,
        "cer_units": cer_units,
        "wer_edits": wer_edits,
        "wer_units": wer_units,
        "utterances": utterances,
        "beam_size": first["beam_size"],
        "compute_type": first["compute_type"],
        "model": first["model"],
        "eval_dir": first["eval_dir"],
        "aggregation": {
            "chunk_starts": STARTS,
            "chunk_size": 100,
        },
    }

    if len(predictions) != utterances:
        raise RuntimeError(
            f"prediction count mismatch: {len(predictions)} != {utterances}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "predictions.json").write_text(
        json.dumps(predictions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
