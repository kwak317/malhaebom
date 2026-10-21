#!/usr/bin/env python3
"""Fail if Git starts tracking local secrets, model assets, or oversized artifacts.

This is a *filename / size / gitignore* guard. It intentionally does not read or
print secret file contents and is not a substitute for the separate secret scan.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_TRACKED_BYTES = 5 * 1024 * 1024
PRIVATE_BASENAMES = frozenset({
    "id_rsa", "id_ed25519", "auth.json", "credentials.json", "secrets.json",
})
PRIVATE_SUFFIXES = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".safetensors", ".ckpt",
    ".pth", ".pt", ".onnx", ".wav", ".mp3", ".flac", ".ogg", ".m4a",
})
PRIVATE_ROOTS = frozenset({
    "local-results", "local-analysis", "data", "datasets", "raw_data",
    "derived_data", "artifacts", "experiments", "outputs",
    "models", "checkpoints", "venv", ".venv", ".venvs", "node_modules",
})
MUST_IGNORE = (
    ".env",
    ".env.job-source-e2e",
    ".env.playmcp/auth.json",
    "local-results/audit-output.json",
    "data/private.wav",
    "models/private.safetensors",
)
MUST_NOT_IGNORE = ("frontend/.env.example",)


def forbidden_path(name: str) -> bool:
    parts = Path(name.replace("\\", "/")).parts
    if not parts:
        return False
    basename = parts[-1].lower()
    if parts[0] in PRIVATE_ROOTS or "node_modules" in parts:
        return True
    if basename == ".env.example":
        return False
    if basename == ".env" or basename.startswith(".env."):
        return True
    if basename in PRIVATE_BASENAMES:
        return True
    if any(basename.endswith(ext) for ext in PRIVATE_SUFFIXES):
        return True
    return False


def tracked_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    )
    return sorted(path for path in result.stdout.decode("utf-8").split("\0") if path)


def is_ignored(root: Path, name: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", name],
        cwd=root, capture_output=True, check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git check-ignore failed for {name}")
    return result.returncode == 0


def audit_repository(root: Path = ROOT) -> tuple[int, list[str]]:
    paths = tracked_paths(root)
    problems: list[str] = []
    for name in paths:
        if forbidden_path(name):
            problems.append(f"disallowed tracked path: {name}")
        file = root / name
        if not file.is_file():
            problems.append(f"tracked file is missing from checkout: {name}")
        elif file.stat().st_size > MAX_TRACKED_BYTES:
            problems.append(f"oversized tracked file: {name}")
    for name in MUST_IGNORE:
        if not is_ignored(root, name):
            problems.append(f"missing ignore rule: {name}")
    for name in MUST_NOT_IGNORE:
        if is_ignored(root, name):
            problems.append(f"example configuration unexpectedly ignored: {name}")
    return len(paths), problems


def main() -> int:
    count, problems = audit_repository()
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"Tracked artifact policy: OK ({count} files; ignore rules verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
