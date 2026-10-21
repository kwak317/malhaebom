#!/usr/bin/env python3
"""Compare baseline, first retrain, and clean-continuation STT on fixed Test B."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT = PROJECT_ROOT / "artifacts" / "stt" / "test-b"
INPUTS = {
    "baseline": ROOT / "baseline" / "metrics.json",
    "retrain": ROOT / "retrain" / "metrics.json",
    "clean_continuation": ROOT / "clean-continuation" / "metrics.json",
}
OUTPUT = ROOT / "comparison.json"
CONDITION_KEYS = ("utterances", "start_index", "beam_size", "compute_type", "eval_dir")


def load(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def delta(candidate: float, baseline: float) -> dict[str, float]:
    return {
        "absolute_delta": candidate - baseline,
        "relative_delta_percent": (
            (candidate - baseline) / baseline * 100 if baseline else 0.0
        ),
    }


def main() -> int:
    metrics = {name: load(path) for name, path in INPUTS.items()}
    baseline = metrics["baseline"]

    for name, current in metrics.items():
        for key in CONDITION_KEYS:
            if current.get(key) != baseline.get(key):
                raise RuntimeError(
                    f"{name}: incompatible evaluation condition for {key}: "
                    f"{current.get(key)!r} != {baseline.get(key)!r}"
                )

    result = {
        "test_set": baseline["eval_dir"],
        "utterances": baseline["utterances"],
        "conditions": {
            key: baseline[key] for key in CONDITION_KEYS if key != "eval_dir"
        },
        "models": {
            name: {
                "model": value["model"],
                "cer_percent": value["cer_percent"],
                "wer_percent": value["wer_percent"],
                "cer_edits": value["cer_edits"],
                "cer_units": value["cer_units"],
                "wer_edits": value["wer_edits"],
                "wer_units": value["wer_units"],
            }
            for name, value in metrics.items()
        },
        "deltas": {
            "retrain_vs_baseline": {
                "cer": delta(metrics["retrain"]["cer_percent"], baseline["cer_percent"]),
                "wer": delta(metrics["retrain"]["wer_percent"], baseline["wer_percent"]),
            },
            "clean_vs_retrain": {
                "cer": delta(
                    metrics["clean_continuation"]["cer_percent"],
                    metrics["retrain"]["cer_percent"],
                ),
                "wer": delta(
                    metrics["clean_continuation"]["wer_percent"],
                    metrics["retrain"]["wer_percent"],
                ),
            },
            "clean_vs_baseline": {
                "cer": delta(
                    metrics["clean_continuation"]["cer_percent"],
                    baseline["cer_percent"],
                ),
                "wer": delta(
                    metrics["clean_continuation"]["wer_percent"],
                    baseline["wer_percent"],
                ),
            },
        },
    }

    ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
