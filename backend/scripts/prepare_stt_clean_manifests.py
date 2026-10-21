#!/usr/bin/env python3
"""Create placeholder-free STT train/validation manifests without touching originals."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "stt" / "handoff-reconstructed"
PLACEHOLDER_RE = re.compile(r"#.+?#|&[^&]+&")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-root", type=Path, default=DEFAULT_ROOT)
    p.add_argument(
        "--output-subdir",
        default="dataset-clean-no-placeholders",
        help="Created below dataset root.",
    )
    return p.parse_args()


def filter_manifest(src: Path, dst: Path) -> dict[str, int]:
    total = kept = removed = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open(encoding="utf-8") as inp, dst.open("w", encoding="utf-8") as out:
        for line in inp:
            if not line.strip():
                continue
            row = json.loads(line)
            total += 1
            text = str(row.get("text", ""))
            if PLACEHOLDER_RE.search(text):
                removed += 1
                continue
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            kept += 1
    return {"total": total, "kept": kept, "removed": removed}


def main() -> int:
    args = parse_args()
    root = args.dataset_root.resolve()
    source_dir = root / "dataset"
    output_dir = root / args.output_subdir
    if output_dir.resolve() == source_dir.resolve():
        raise RuntimeError("refusing to overwrite original dataset manifests")

    summary = {}
    for split in ("train", "validation"):
        summary[split] = filter_manifest(
            source_dir / f"{split}.jsonl",
            output_dir / f"{split}.jsonl",
        )

    metadata = {
        "filter": "remove rows whose text contains #...# or &...& placeholders",
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "splits": summary,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
