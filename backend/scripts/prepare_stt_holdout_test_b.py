#!/usr/bin/env python3
"""Create clean source-disjoint STT Test B, excluding the already-seen Test A sources."""

from __future__ import annotations

import argparse
import io
import json
import re
import wave
import zipfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "data" / "stt" / "handoff-reconstructed"
AIHUB_ROOT = (
    PROJECT_ROOT
    / "data"
    / "stt"
    / "aihub"
    / "119"
    / "014.한국어_방언_발화_데이터(경상도)"
    / "01.데이터"
)
AUDIO_ZIP = (
    AIHUB_ROOT
    / "2.Validation"
    / "(new3)원천데이터"
    / "(비식별화완료)경상도_2.zip"
)
LABEL_ZIP = (
    AIHUB_ROOT
    / "2.Validation"
    / "(new3)라벨링데이터"
    / "(비식별화완료)경상도_학습데이터_2.zip"
)
DEFAULT_TEST_A = PROJECT_ROOT / "data" / "stt" / "holdout-test"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "stt" / "holdout-test-b-clean"
SOURCE_RE = re.compile(r"(DKSR\d+)")
PLACEHOLDER_RE = re.compile(r"#.+?#|&[^&]+&")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-root", type=Path, default=DATASET_ROOT)
    p.add_argument("--test-a", type=Path, default=DEFAULT_TEST_A)
    p.add_argument("--audio-zip", type=Path, default=AUDIO_ZIP)
    p.add_argument("--label-zip", type=Path, default=LABEL_ZIP)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--source-count", type=int, default=20)
    p.add_argument("--utterances-per-source", type=int, default=25)
    p.add_argument("--plan-only", action="store_true")
    return p.parse_args()


def used_sources(manifest: Path) -> set[str]:
    sources: set[str] = set()
    with manifest.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            match = SOURCE_RE.search(str(row.get("audio", "")))
            if not match:
                raise ValueError(f"cannot infer source from {row.get('audio')}")
            sources.add(match.group(1))
    return sources


def test_a_sources(test_a: Path) -> set[str]:
    metadata = test_a / "metadata.json"
    if metadata.is_file():
        data = json.loads(metadata.read_text(encoding="utf-8"))
        values = data.get("selected_sources", [])
        if isinstance(values, list):
            return {str(value) for value in values}
    manifest = test_a / "manifest.jsonl"
    if not manifest.is_file():
        raise FileNotFoundError(f"cannot find Test A metadata/manifest: {test_a}")
    sources = set()
    with manifest.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                sources.add(str(json.loads(line)["source_id"]))
    return sources


def reference_of(utterance: dict[str, Any]) -> str | None:
    value = (
        utterance.get("dialect_form")
        or utterance.get("form")
        or utterance.get("standard_form")
    )
    return str(value) if value else None


def clean_utterances(label: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for utterance in label.get("utterance", []):
        reference = reference_of(utterance)
        if not reference or PLACEHOLDER_RE.search(reference):
            continue
        rows.append(utterance)
    return rows


def available_ids(label_zip: zipfile.ZipFile, audio_zip: zipfile.ZipFile) -> list[str]:
    labels = {Path(x).stem for x in label_zip.namelist() if x.lower().endswith(".json")}
    audio = {Path(x).stem for x in audio_zip.namelist() if x.lower().endswith(".wav")}
    return sorted(labels & audio)


def extract(
    source_id: str,
    audio_zip: zipfile.ZipFile,
    label_zip: zipfile.ZipFile,
    output_audio: Path,
    utterance_limit: int,
) -> list[dict[str, Any]]:
    label = json.loads(label_zip.read(f"{source_id}.json"))
    utterances = clean_utterances(label)[:utterance_limit]
    if len(utterances) < utterance_limit:
        raise RuntimeError(
            f"{source_id}: only {len(utterances)} clean utterances, need {utterance_limit}"
        )
    source_audio = audio_zip.read(f"{source_id}.wav")
    with wave.open(io.BytesIO(source_audio), "rb") as src:
        params = src.getparams()
        sample_rate = src.getframerate()
        if params.comptype != "NONE":
            raise ValueError(f"{source_id}: unsupported compression {params.comptype}")
        frames = src.readframes(src.getnframes())

    bytes_per_frame = params.sampwidth * params.nchannels
    rows = []
    for utt in utterances:
        start_frame = round(float(utt["start"]) * sample_rate)
        end_frame = round(float(utt["end"]) * sample_rate)
        clip = frames[start_frame * bytes_per_frame : end_frame * bytes_per_frame]
        uid = str(utt["id"])
        filename = uid.replace(".", "_") + ".wav"
        with wave.open(str(output_audio / filename), "wb") as dst:
            dst.setparams(params)
            dst.writeframes(clip)
        rows.append(
            {
                "id": uid,
                "source_id": source_id,
                "audio": f"audio/{filename}",
                "reference": reference_of(utt),
                "standard_reference": utt.get("standard_form"),
                "start": utt["start"],
                "end": utt["end"],
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    root = args.dataset_root.resolve()
    used_train = used_sources(root / "dataset" / "train.jsonl")
    used_validation = used_sources(root / "dataset" / "validation.jsonl")
    seen_test_a = test_a_sources(args.test_a.resolve())
    excluded = used_train | used_validation | seen_test_a

    with zipfile.ZipFile(args.audio_zip) as audio_zip, zipfile.ZipFile(
        args.label_zip
    ) as label_zip:
        eligible = []
        for source_id in available_ids(label_zip, audio_zip):
            if source_id in excluded:
                continue
            label = json.loads(label_zip.read(f"{source_id}.json"))
            if len(clean_utterances(label)) >= args.utterances_per_source:
                eligible.append(source_id)

        if len(eligible) < args.source_count:
            raise RuntimeError(
                f"only {len(eligible)} eligible clean sources; need {args.source_count}"
            )
        selected = eligible[: args.source_count]
        plan = {
            "train_sources": len(used_train),
            "validation_sources": len(used_validation),
            "test_a_sources_excluded": len(seen_test_a),
            "excluded_source_union": len(excluded),
            "eligible_clean_sources": len(eligible),
            "selected_sources": selected,
            "source_count": len(selected),
            "utterances_per_source": args.utterances_per_source,
            "placeholder_policy": "exclude any reference containing #...# or &...&",
        }
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        if args.plan_only:
            print("STT clean Test B plan PASSED")
            return 0

        output = args.output.resolve()
        if output.exists() and any(output.iterdir()):
            raise RuntimeError(f"Test B output is not empty: {output}")
        output_audio = output / "audio"
        output_audio.mkdir(parents=True, exist_ok=True)
        rows = []
        for source_id in selected:
            rows.extend(
                extract(
                    source_id,
                    audio_zip,
                    label_zip,
                    output_audio,
                    args.utterances_per_source,
                )
            )

    selected_sources = {row["source_id"] for row in rows}
    overlap = selected_sources & excluded
    if overlap:
        raise RuntimeError(f"Test B leakage detected: {sorted(overlap)}")
    if any(PLACEHOLDER_RE.search(str(row["reference"])) for row in rows):
        raise RuntimeError("Test B contains placeholder references")

    output = args.output.resolve()
    with (output / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    metadata = {
        **plan,
        "rows": len(rows),
        "source_overlap_with_train_validation_or_test_a": 0,
        "source_archive": str(args.audio_zip),
        "label_archive": str(args.label_zip),
    }
    (output / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"created clean Test B: {len(rows)} utterances -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
