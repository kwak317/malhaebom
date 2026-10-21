#!/usr/bin/env python3
"""Convert a training-style STT JSONL manifest into evaluator format without copying audio."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--name", default="eval")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def resolve_audio(value: str, source_manifest: Path) -> Path:
    raw = Path(value).expanduser()
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend(
            [
                PROJECT_ROOT / raw,
                source_manifest.parent / raw,
            ]
        )
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file():
            return resolved
    raise FileNotFoundError(f"cannot resolve audio path: {value}")


def main() -> int:
    args = parse_args()
    source = args.input.resolve()
    output = args.output_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    manifest = output / "manifest.jsonl"
    metadata = output / "metadata.json"
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise RuntimeError(f"output is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    rows = []
    seen_ids: set[str] = set()
    with source.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            audio_value = raw.get("audio")
            reference = raw.get("reference") or raw.get("text")
            if not isinstance(audio_value, str) or not audio_value:
                raise ValueError(f"{source}:{index}: missing audio")
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError(f"{source}:{index}: missing reference/text")

            audio = resolve_audio(audio_value, source)
            base_id = (
                str(raw.get("id") or raw.get("utterance_id") or audio.stem).strip()
                or f"{args.name}-{index:06d}"
            )
            uid = base_id
            if uid in seen_ids:
                uid = f"{base_id}-{index:06d}"
            seen_ids.add(uid)

            rows.append(
                {
                    "id": uid,
                    "source_id": raw.get("source_id"),
                    "audio": os.path.relpath(audio, output),
                    "reference": reference,
                }
            )

    if not rows:
        raise ValueError(f"no rows in {source}")

    with manifest.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "name": args.name,
        "source_manifest": str(source),
        "output_dir": str(output),
        "rows": len(rows),
        "audio_missing": 0,
        "format": "evaluate_stt_ct2 manifest",
    }
    metadata.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
