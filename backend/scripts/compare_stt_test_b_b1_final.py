#!/usr/bin/env python3
"""Compare final fixed Test B metrics for B0 clean-continuation and B1 checkpoint-300."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B0_PATH = ROOT / "artifacts/stt/test-b/clean-continuation/metrics.json"
B1_PATH = ROOT / "artifacts/stt/test-b/b1-cp300-final/metrics.json"
OUTPUT = ROOT / "artifacts/stt/test-b/b0-vs-b1-final.json"


def load(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    b0 = load(B0_PATH)
    b1 = load(B1_PATH)
    result = {
        "evaluation": "fixed clean Test B final regression confirmation",
        "rows": [
            {
                "model": "b0-clean",
                "cer_percent": b0["cer_percent"],
                "wer_percent": b0["wer_percent"],
                "cer_edits": b0["cer_edits"],
                "wer_edits": b0["wer_edits"],
                "utterances": b0["utterances"],
                "delta_cer_pp_vs_b0": 0.0,
                "delta_wer_pp_vs_b0": 0.0,
            },
            {
                "model": "b1-cp300",
                "cer_percent": b1["cer_percent"],
                "wer_percent": b1["wer_percent"],
                "cer_edits": b1["cer_edits"],
                "wer_edits": b1["wer_edits"],
                "utterances": b1["utterances"],
                "delta_cer_pp_vs_b0": b1["cer_percent"] - b0["cer_percent"],
                "delta_wer_pp_vs_b0": b1["wer_percent"] - b0["wer_percent"],
            },
        ],
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in result["rows"]:
        print(
            f"{row['model']}: CER={row['cer_percent']:.4f}% "
            f"WER={row['wer_percent']:.4f}% "
            f"ΔCER={row['delta_cer_pp_vs_b0']:+.4f}pp "
            f"ΔWER={row['delta_wer_pp_vs_b0']:+.4f}pp"
        )
    print(f"comparison: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
