#!/usr/bin/env python3
"""Prepare the frozen 30-recording real-user STT diagnostic set from a local ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCRIPT = (
    ROOT
    / "docs/experiments/stt/assets/2026-09-27_real-user-recording-script.md"
)
DEFAULT_OUTPUT = ROOT / "local-results/stt-real-user-devset"
EXPECTED_ZIP_SHA256 = "c53c3161562a9b86ef5b5da27772eca0cc6dea7f1d80082e7e619c46fe5fbf39"
EXPECTED_SCRIPT_SHA256 = "5fae3039e5f0ca15728e7d8446d70411aa0598c0fc793b66937a1903547f2771"
EXPECTED_ROWS = 30


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_expected_sha256(label: str, actual: str, expected: str) -> None:
    normalized = expected.strip().lower()
    if not normalized:
        raise ValueError(f"{label} expected SHA-256 must not be empty")
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError(f"{label} expected SHA-256 must be 64 lowercase hex characters")
    if actual.lower() != normalized:
        raise RuntimeError(
            f"{label} fingerprint mismatch: expected={normalized}, actual={actual}"
        )


def validate_canonical_fingerprints(zip_sha256: str, script_sha256: str) -> None:
    validate_expected_sha256("canonical audio ZIP", zip_sha256, EXPECTED_ZIP_SHA256)
    validate_expected_sha256("canonical reference script", script_sha256, EXPECTED_SCRIPT_SHA256)


def group_for_index(index: int) -> str:
    if 1 <= index <= 10:
        return "general-interview"
    if 11 <= index <= 18:
        return "technical"
    if 19 <= index <= 24:
        return "numbers-english-stress"
    if 25 <= index <= 30:
        return "natural-long"
    raise ValueError(f"unsupported recording index: {index}")


def parse_references(text: str) -> dict[int, str]:
    heading = re.compile(r"^###\s+(\d{2})\.\s+.*$", re.MULTILINE)
    matches = list(heading.finditer(text))
    references: dict[int, str] = {}

    for position, match in enumerate(matches):
        index = int(match.group(1))
        if index in references:
            raise ValueError(f"duplicate script index: {index}")
        end = matches[position + 1].start() if position + 1 < len(matches) else len(text)
        lines: list[str] = []
        for line in text[match.end() : end].splitlines():
            stripped = line.strip()
            if not stripped or stripped == "---":
                continue
            if stripped.startswith("#"):
                break
            lines.append(stripped)
        references[index] = " ".join(lines).strip()

    return references


def audio_entries(archive: zipfile.ZipFile) -> dict[int, zipfile.ZipInfo]:
    pattern = re.compile(r"(?:^|/)(?:소리 )?녹음 \((\d+)\)\.m4a$")
    entries: dict[int, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        normalized = info.filename.replace("\\", "/")
        match = pattern.search(normalized)
        if not match:
            continue
        index = int(match.group(1))
        if index in entries:
            raise ValueError(f"duplicate recording index in ZIP: {index}")
        entries[index] = info
    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-zip", type=Path, required=True)
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audio_zip = args.audio_zip.expanduser().resolve()
    script = args.script.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not audio_zip.is_file():
        raise FileNotFoundError(audio_zip)
    if not script.is_file():
        raise FileNotFoundError(script)

    zip_sha256 = sha256_file(audio_zip)
    script_sha256 = sha256_file(script)
    validate_canonical_fingerprints(zip_sha256, script_sha256)

    references = parse_references(script.read_text(encoding="utf-8"))
    expected_indexes = list(range(1, EXPECTED_ROWS + 1))
    if sorted(references) != expected_indexes:
        raise RuntimeError(f"script indexes mismatch: {sorted(references)}")

    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(audio_zip) as archive:
        entries = audio_entries(archive)
        if sorted(entries) != expected_indexes:
            raise RuntimeError(f"audio indexes mismatch: {sorted(entries)}")

        for index in expected_indexes:
            destination = audio_dir / f"{index:02d}.m4a"
            with archive.open(entries[index]) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)

    manifest = output_dir / "manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as handle:
        for index in expected_indexes:
            handle.write(
                json.dumps(
                    {
                        "id": f"real-{index:02d}",
                        "source_id": f"recording-{index}",
                        "audio": f"audio/{index:02d}.m4a",
                        "reference": references[index],
                        "group": group_for_index(index),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    metadata = {
        "schema_version": 1,
        "rows": EXPECTED_ROWS,
        "source_zip_sha256": zip_sha256,
        "expected_zip_sha256": EXPECTED_ZIP_SHA256,
        "zip_fingerprint_override": False,
        "script_sha256": script_sha256,
        "expected_script_sha256": EXPECTED_SCRIPT_SHA256,
        "script_fingerprint_override": False,
        "script": str(script),
        "groups": {
            "general-interview": "01-10",
            "technical": "11-18",
            "numbers-english-stress": "19-24",
            "natural-long": "25-30",
        },
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(output_dir),
                "rows": EXPECTED_ROWS,
                "zip_sha256": zip_sha256,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
