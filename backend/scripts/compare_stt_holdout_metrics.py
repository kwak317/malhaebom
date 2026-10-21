#!/usr/bin/env python3
"""Compare baseline and retrained STT metrics on the same fixed holdout."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE = PROJECT_ROOT / "artifacts/stt/baseline-holdout/metrics.json"
CANDIDATE = PROJECT_ROOT / "artifacts/stt/candidate-holdout/metrics.json"


def load(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    baseline = load(BASELINE)
    candidate = load(CANDIDATE)

    for key in ("utterances", "beam_size", "compute_type", "eval_dir"):
        if baseline.get(key) != candidate.get(key):
            raise RuntimeError(
                f"incompatible evaluation condition for {key}: "
                f"{baseline.get(key)!r} != {candidate.get(key)!r}"
            )

    result = {
        "utterances": baseline["utterances"],
        "baseline_model": baseline["model"],
        "candidate_model": candidate["model"],
        "cer_percent": {
            "baseline": baseline["cer_percent"],
            "candidate": candidate["cer_percent"],
            "absolute_delta": candidate["cer_percent"] - baseline["cer_percent"],
            "relative_delta_percent": (
                (candidate["cer_percent"] - baseline["cer_percent"])
                / baseline["cer_percent"]
                * 100
                if baseline["cer_percent"]
                else 0.0
            ),
        },
        "wer_percent": {
            "baseline": baseline["wer_percent"],
            "candidate": candidate["wer_percent"],
            "absolute_delta": candidate["wer_percent"] - baseline["wer_percent"],
            "relative_delta_percent": (
                (candidate["wer_percent"] - baseline["wer_percent"])
                / baseline["wer_percent"]
                * 100
                if baseline["wer_percent"]
                else 0.0
            ),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
