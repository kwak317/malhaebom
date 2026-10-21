#!/usr/bin/env python3
"""Validate the clean-continuation experiment inputs without training."""

from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/stt/handoff-reconstructed"
CLEAN = DATASET / "dataset-clean-no-placeholders"
TEST_B = ROOT / "data/stt/holdout-test-b-clean"
ADAPTER = ROOT / "artifacts/stt/whisper-medium-busan-qlora-retrain/best_adapter"
PLACEHOLDER_RE = re.compile(r"#.+?#|&[^&]+&")
SOURCE_RE = re.compile(r"(DKSR\d+)")

def rows(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def sources_from_train_manifest(path: Path) -> set[str]:
    result=set()
    for row in rows(path):
        m=SOURCE_RE.search(str(row["audio"]))
        if not m:
            raise RuntimeError(f"source id missing: {row['audio']}")
        result.add(m.group(1))
    return result

train=list(rows(CLEAN/"train.jsonl"))
validation=list(rows(CLEAN/"validation.jsonl"))
if len(train)!=48000 or len(validation)!=4802:
    raise RuntimeError(f"unexpected clean sizes: {len(train)}, {len(validation)}")
if any(PLACEHOLDER_RE.search(str(r["text"])) for r in train+validation):
    raise RuntimeError("placeholder remained in clean manifests")

test_b=list(rows(TEST_B/"manifest.jsonl"))
if len(test_b)!=500:
    raise RuntimeError(f"unexpected Test B size: {len(test_b)}")
if any(PLACEHOLDER_RE.search(str(r["reference"])) for r in test_b):
    raise RuntimeError("placeholder remained in Test B")

train_sources=sources_from_train_manifest(DATASET/"dataset/train.jsonl")
val_sources=sources_from_train_manifest(DATASET/"dataset/validation.jsonl")
test_a_meta=json.loads((ROOT/"data/stt/holdout-test/metadata.json").read_text(encoding="utf-8"))
test_a_sources=set(test_a_meta["selected_sources"])
test_b_sources={str(r["source_id"]) for r in test_b}
overlap=test_b_sources & (train_sources|val_sources|test_a_sources)
if overlap:
    raise RuntimeError(f"Test B source leakage: {sorted(overlap)}")

adapter_weight=ADAPTER/"adapter_model.safetensors"
if not adapter_weight.is_file():
    raise FileNotFoundError(adapter_weight)

cfg=json.loads((ROOT/"[REDACTED].json").read_text(encoding="utf-8"))
result={
    "clean_train_rows":len(train),
    "clean_validation_rows":len(validation),
    "test_b_rows":len(test_b),
    "test_b_sources":len(test_b_sources),
    "test_b_source_overlap":0,
    "init_adapter":str(ADAPTER),
    "adapter_weight_bytes":adapter_weight.stat().st_size,
    "learning_rate":cfg["learning_rate"],
    "epochs":cfg["epochs"],
    "effective_batch":cfg["batch_size"]*cfg["grad_accum"],
    "output_dir":cfg["output_dir"],
}
print(json.dumps(result,ensure_ascii=False,indent=2))
