#!/usr/bin/env python3
"""Download the public Malhaebom STT CTranslate2 model release with gdown.

The public Drive folder must be accessible without Google login. This script
installs a pinned gdown copy under .cache/ so project/runtime environments are
not modified, downloads into an ignored staging directory, verifies every
published model file, and then moves the verified model into models/stt/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

GDOWN_VERSION = "6.4.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "configs" / "stt" / "public_model_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and verify the public Malhaebom STT model release."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Public release manifest JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Override the final model directory.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify an existing local model without downloading.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing invalid output/staging directory.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"model_dir_name", "files"}
    missing = required - set(data)
    if missing:
        raise RuntimeError(f"manifest missing keys: {sorted(missing)}")
    for item in data["files"]:
        item_missing = {"name", "drive_file_id", "size_bytes", "sha256"} - set(item)
        if item_missing:
            raise RuntimeError(
                f"manifest file entry missing keys for {item.get('name', '<unnamed>')}: "
                f"{sorted(item_missing)}"
            )
    return data


def verify_model_dir(model_dir: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for item in manifest["files"]:
        path = model_dir / item["name"]
        if not path.is_file():
            errors.append(f"missing: {path.name}")
            continue

        actual_size = path.stat().st_size
        expected_size = int(item["size_bytes"])
        if actual_size != expected_size:
            errors.append(
                f"size mismatch: {path.name}: expected={expected_size} actual={actual_size}"
            )
            continue

        actual_hash = sha256_file(path)
        expected_hash = str(item["sha256"]).lower()
        if actual_hash.lower() != expected_hash:
            errors.append(
                f"sha256 mismatch: {path.name}: expected={expected_hash} actual={actual_hash}"
            )
    return errors


def ensure_gdown() -> tuple[Path, dict[str, str]]:
    tool_dir = PROJECT_ROOT / ".cache" / "tools" / f"gdown-{GDOWN_VERSION}"
    marker = tool_dir / "gdown" / "__init__.py"
    if not marker.exists():
        tool_dir.mkdir(parents=True, exist_ok=True)
        print(f"[setup] installing gdown=={GDOWN_VERSION} into {tool_dir}")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--target",
                str(tool_dir),
                f"gdown=={GDOWN_VERSION}",
            ],
            check=True,
        )

    env = os.environ.copy()
    previous = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(tool_dir) if not previous else str(tool_dir) + os.pathsep + previous
    )
    return tool_dir, env


def download_public_files(manifest: dict[str, Any], staging: Path) -> None:
    _, env = ensure_gdown()
    staging.mkdir(parents=True, exist_ok=True)
    for item in manifest["files"]:
        destination = staging / str(item["name"])
        print(f"[download] {item['name']}")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "gdown",
                str(item["drive_file_id"]),
                "-O",
                str(destination),
                "--no-cookies",
                "--continue",
                "--timeout",
                "60",
                "--retries",
                "3",
            ],
            env=env,
            check=True,
        )


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)

    output = (
        args.output.resolve()
        if args.output
        else (
            PROJECT_ROOT
            / "models"
            / "stt"
            / str(manifest["model_dir_name"])
        )
    )

    if output.exists():
        print(f"[verify] existing model: {output}")
        errors = verify_model_dir(output, manifest)
        if not errors:
            print("[ok] existing model matches the public release manifest")
            return 0
        if args.verify_only:
            for error in errors:
                print(f"[error] {error}", file=sys.stderr)
            return 1
        if not args.force:
            print(
                "[error] existing model failed verification; rerun with --force "
                "to replace it",
                file=sys.stderr,
            )
            for error in errors:
                print(f"[error] {error}", file=sys.stderr)
            return 1
        shutil.rmtree(output)

    if args.verify_only:
        print(f"[error] model directory does not exist: {output}", file=sys.stderr)
        return 1

    staging = output.parent / f".{output.name}.gdown"
    if staging.exists() and args.force:
        shutil.rmtree(staging)

    download_public_files(manifest, staging)

    print(f"[verify] downloaded model: {staging}")
    errors = verify_model_dir(staging, manifest)
    if errors:
        for error in errors:
            print(f"[error] {error}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        shutil.rmtree(output)
    shutil.move(str(staging), str(output))

    print(f"[ok] installed verified model at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
