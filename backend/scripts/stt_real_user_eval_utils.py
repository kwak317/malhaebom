from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Callable

from score_stt_spoken_form import score_records

CT2_MODEL_FILES = (
    "config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.json",
    "preprocessor_config.json",
)


def model_complete(path: Path) -> bool:
    return all((path / name).is_file() for name in CT2_MODEL_FILES)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ct2_model_fingerprint(path: Path) -> str:
    resolved = path.expanduser().resolve()
    if not model_complete(resolved):
        raise FileNotFoundError(f"incomplete CT2 model: {resolved}")
    digest = hashlib.sha256()
    for name in CT2_MODEL_FILES:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(resolved / name).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def load_rows(eval_dir: Path, max_samples: int | None = None) -> list[dict[str, Any]]:
    manifest = eval_dir / "manifest.jsonl"
    if not manifest.is_file():
        raise FileNotFoundError(f"missing manifest: {manifest}")

    rows = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if max_samples is not None:
        if max_samples < 1:
            raise ValueError("--max-samples must be >= 1")
        rows = rows[:max_samples]
    if not rows:
        raise ValueError("evaluation set is empty")

    for row in rows:
        audio = eval_dir / str(row["audio"])
        if not audio.is_file():
            raise FileNotFoundError(audio)
        if not row.get("reference"):
            raise ValueError(f"empty reference: {row.get('id')}")
    return rows


def devset_provenance(eval_dir: Path, rows: list[dict[str, Any]]) -> dict[str, str | int]:
    manifest = eval_dir / "manifest.jsonl"
    manifest_sha256 = sha256_file(manifest)
    audio_digest = hashlib.sha256()
    for row in rows:
        relative = str(row["audio"])
        audio_sha256 = sha256_file(eval_dir / relative)
        audio_digest.update(
            json.dumps([row["id"], relative, audio_sha256], ensure_ascii=False).encode("utf-8")
            + b"\n"
        )
    audio_set_sha256 = audio_digest.hexdigest()
    combined = hashlib.sha256(
        f"{manifest_sha256}\n{audio_set_sha256}\n{len(rows)}".encode("ascii")
    ).hexdigest()
    return {
        "row_count": len(rows),
        "manifest_sha256": manifest_sha256,
        "audio_set_sha256": audio_set_sha256,
        "data_fingerprint_sha256": combined,
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def timing_metrics(records: list[dict[str, Any]]) -> dict[str, float | int | None]:
    latencies = [float(row["processing_time_sec"]) for row in records]
    rtfs = [float(row["rtf"]) for row in records if row.get("rtf") is not None]
    audio_total = sum(float(row["audio_duration_sec"]) for row in records)
    processing_total = sum(latencies)
    return {
        "utterances": len(records),
        "audio_duration_sec": audio_total,
        "processing_time_sec": processing_total,
        "aggregate_rtf": processing_total / audio_total if audio_total > 0 else None,
        "latency_p50_sec": statistics.median(latencies) if latencies else None,
        "latency_p95_sec": percentile(latencies, 0.95),
        "rtf_p50": statistics.median(rtfs) if rtfs else None,
        "rtf_p95": percentile(rtfs, 0.95),
    }


def score_subset(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    return {
        "raw": score_records(records, spoken_form=False),
        "spoken_form_normalized": score_records(records, spoken_form=True),
    }


def score_groups(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        groups.setdefault(str(row.get("group", "ungrouped")), []).append(row)

    core = [
        row
        for row in records
        if row.get("group") != "numbers-english-stress"
    ]
    return {
        "overall": score_subset(records),
        "core_excluding_stress": score_subset(core),
        "groups": {
            name: score_subset(rows)
            for name, rows in sorted(groups.items())
        },
    }


def load_matching_completed_metrics(
    path: Path,
    *,
    expected_run: dict[str, Any],
    row_count: int,
    summary_validator: Callable[[dict[str, Any]], Any],
) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != 2:
        return None

    run = payload.get("run")
    if not isinstance(run, dict):
        return None
    if any(run.get(key) != value for key, value in expected_run.items()):
        return None

    predictions_path = path.parent / "predictions.json"
    try:
        predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
        if not isinstance(predictions, list) or len(predictions) != row_count:
            return None
        required = (
            "id",
            "reference",
            "prediction",
            "processing_time_sec",
            "audio_duration_sec",
        )
        if any(
            not isinstance(row, dict) or not all(key in row for key in required)
            for row in predictions
        ):
            return None
        summary_validator(payload)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    return payload
