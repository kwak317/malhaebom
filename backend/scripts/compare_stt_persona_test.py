#!/usr/bin/env python3
"""Compare held-out new-persona STT test metrics for B0/B1/B2 candidates."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/stt/persona-test"
ORDER = ["b0-clean", "b1-cp300", "b2-cp200", "b2-cp391"]


def load_metrics(name: str) -> dict:
    path = OUTPUT_ROOT / name / "metrics.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def main() -> int:
    metrics = {name: load_metrics(name) for name in ORDER}
    baseline = metrics["b0-clean"]
    rows = []
    for name in ORDER:
        data = metrics[name]
        rows.append(
            {
                "model": name,
                "cer_percent": data["cer_percent"],
                "wer_percent": data["wer_percent"],
                "cer_edits": data["cer_edits"],
                "wer_edits": data["wer_edits"],
                "utterances": data["utterances"],
                "delta_cer_pp_vs_b0": data["cer_percent"] - baseline["cer_percent"],
                "delta_wer_pp_vs_b0": data["wer_percent"] - baseline["wer_percent"],
            }
        )

    result = {
        "evaluation": "held-out new-persona test",
        "baseline": "b0-clean",
        "rows": rows,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_ROOT / "comparison.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("| model | CER | WER | ΔCER vs B0 | ΔWER vs B0 |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for row in rows:
        print(
            f"| {row['model']} | {row['cer_percent']:.4f}% | {row['wer_percent']:.4f}% | "
            f"{row['delta_cer_pp_vs_b0']:+.4f}pp | {row['delta_wer_pp_vs_b0']:+.4f}pp |"
        )
    print(f"comparison: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
