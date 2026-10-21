#!/usr/bin/env python3
"""Download and verify the public Malhaebom TTS model releases with gdown."""

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
DEFAULT_MANIFEST = PROJECT_ROOT / "configs" / "tts" / "public_model_manifest.json"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "models" / "tts"
DEFAULT_STAGING_ROOT = PROJECT_ROOT / ".cache" / "downloads" / "tts-public"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and verify the public Malhaebom TTS model releases."
    )
    parser.add_argument(
        "--model",
        choices=("questioner", "coach", "all"),
        default="all",
        help="Select which TTS model bundle to install.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Public TTS release manifest JSON.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root directory that receives questioner_candidate04/ and coach_candidate01/.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify selected existing local models without downloading.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing invalid selected model directory.",
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
    required = {"models", "files"}
    missing = required - set(data)
    if missing:
        raise RuntimeError(f"manifest missing keys: {sorted(missing)}")

    for model_key in ("questioner", "coach"):
        if model_key not in data["models"]:
            raise RuntimeError(f"manifest missing model: {model_key}")
        model_missing = {"speaker", "dir_name"} - set(data["models"][model_key])
        if model_missing:
            raise RuntimeError(
                f"manifest model {model_key} missing keys: {sorted(model_missing)}"
            )

    for item in data["files"]:
        item_missing = {"path", "drive_file_id", "size_bytes", "sha256"} - set(item)
        if item_missing:
            raise RuntimeError(
                f"manifest file entry missing keys for {item.get('path', '<unnamed>')}: "
                f"{sorted(item_missing)}"
            )
    return data


def selected_model_keys(selection: str) -> tuple[str, ...]:
    return ("questioner", "coach") if selection == "all" else (selection,)


def entries_for_model(manifest: dict[str, Any], model_key: str) -> list[dict[str, Any]]:
    dir_name = str(manifest["models"][model_key]["dir_name"])
    prefix = dir_name + "/"
    entries = [item for item in manifest["files"] if str(item["path"]).startswith(prefix)]
    if not entries:
        raise RuntimeError(f"manifest has no files for model {model_key}")
    return entries


def verify_entries(root: Path, entries: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for item in entries:
        path = root / str(item["path"])
        if not path.is_file():
            errors.append(f"missing: {item['path']}")
            continue

        actual_size = path.stat().st_size
        expected_size = int(item["size_bytes"])
        if actual_size != expected_size:
            errors.append(
                f"size mismatch: {item['path']}: expected={expected_size} actual={actual_size}"
            )
            continue

        actual_hash = sha256_file(path)
        expected_hash = str(item["sha256"]).lower()
        if actual_hash.lower() != expected_hash:
            errors.append(
                f"sha256 mismatch: {item['path']}: expected={expected_hash} actual={actual_hash}"
            )
    return errors


def ensure_gdown() -> dict[str, str]:
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
    return env


def download_entries(
    manifest: dict[str, Any],
    model_key: str,
    entries: list[dict[str, Any]],
    output_root: Path,
    force: bool,
) -> None:
    dir_name = str(manifest["models"][model_key]["dir_name"])
    output_dir = output_root / dir_name

    if output_dir.exists():
        existing_errors = verify_entries(output_root, entries)
        if not existing_errors:
            print(f"[ok] existing {model_key} model matches public release manifest")
            return
        if not force:
            print(
                f"[error] existing {model_key} model failed verification; "
                "rerun with --force to replace it",
                file=sys.stderr,
            )
            for error in existing_errors:
                print(f"[error] {error}", file=sys.stderr)
            raise RuntimeError(f"invalid existing {model_key} model")
        shutil.rmtree(output_dir)

    staging_root = DEFAULT_STAGING_ROOT
    staging_model = staging_root / dir_name
    if staging_model.exists() and force:
        shutil.rmtree(staging_model)
    staging_model.mkdir(parents=True, exist_ok=True)

    env = ensure_gdown()
    for item in entries:
        rel = Path(str(item["path"]))
        rel_inside_model = Path(*rel.parts[1:])
        destination = staging_model / rel_inside_model
        destination.parent.mkdir(parents=True, exist_ok=True)
        print(f"[download] {item['path']}")
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

    stage_errors = []
    for item in entries:
        rel = Path(str(item["path"]))
        staged_path = staging_root / rel
        if not staged_path.is_file():
            stage_errors.append(f"missing: {item['path']}")
            continue
        actual_size = staged_path.stat().st_size
        expected_size = int(item["size_bytes"])
        if actual_size != expected_size:
            stage_errors.append(
                f"size mismatch: {item['path']}: expected={expected_size} actual={actual_size}"
            )
            continue
        actual_hash = sha256_file(staged_path)
        if actual_hash.lower() != str(item["sha256"]).lower():
            stage_errors.append(f"sha256 mismatch: {item['path']}")

    if stage_errors:
        for error in stage_errors:
            print(f"[error] {error}", file=sys.stderr)
        raise RuntimeError(f"downloaded {model_key} model failed verification")

    output_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(staging_model), str(output_dir))
    print(f"[ok] installed verified {model_key} model at {output_dir}")


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest.resolve())
    output_root = args.output_root.resolve()
    keys = selected_model_keys(args.model)

    if args.verify_only:
        failed = False
        for model_key in keys:
            entries = entries_for_model(manifest, model_key)
            errors = verify_entries(output_root, entries)
            if errors:
                failed = True
                for error in errors:
                    print(f"[error] {model_key}: {error}", file=sys.stderr)
            else:
                print(f"[ok] {model_key} model matches public release manifest")
        return 1 if failed else 0

    for model_key in keys:
        entries = entries_for_model(manifest, model_key)
        download_entries(manifest, model_key, entries, output_root, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
