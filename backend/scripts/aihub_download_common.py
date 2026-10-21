#!/usr/bin/env python3
"""Shared, dependency-free helpers for approved AI Hub dataset downloads.

The module intentionally keeps the API key out of logs and tracked files.  AI Hub's
current official CLI accepts the key as a command-line argument for download mode,
so the key is briefly visible to the local OS process table while aihubshell runs.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AIHUBSHELL_URL = "https://api.aihub.or.kr/api/aihubshell.do"
LOCAL_SHELL = PROJECT_ROOT / ".cache" / "aihub" / "aihubshell"
API_KEY_NAMES = ("AIHUB_API_KEY", "AIHUB_APIKEY")

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TREE_LINE = re.compile(r"^(?P<prefix>(?:(?:│| ) )*)(?:├─|└─)(?P<body>.*)$")
FILE_INFO = re.compile(
    r"^(?P<name>.*?)\s*\|\s*(?P<size>[^|]+?)\s*\|\s*(?P<filekey>\d+)\s*$"
)


@dataclass(frozen=True)
class AIHubFile:
    path: str
    name: str
    size: str
    filekey: str


def _strip_optional_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv(path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries without adding python-dotenv as a dependency."""
    env_path = path or (PROJECT_ROOT / ".env")
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        os.environ.setdefault(key, _strip_optional_quotes(value))


def get_api_key() -> str:
    load_dotenv()
    for name in API_KEY_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(
        "AI Hub API key not found. Put AIHUB_API_KEY=<key> in the project .env "
        "or export AIHUB_API_KEY in the shell."
    )


def ensure_aihubshell(*, install: bool = True) -> Path:
    configured = os.environ.get("AIHUBSHELL_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"AIHUBSHELL_PATH does not point to a file: {path}")
        return path

    global_shell = shutil.which("aihubshell")
    if global_shell:
        return Path(global_shell)

    if LOCAL_SHELL.is_file():
        LOCAL_SHELL.chmod(LOCAL_SHELL.stat().st_mode | stat.S_IXUSR)
        return LOCAL_SHELL

    if not install:
        raise SystemExit(
            "aihubshell is not installed. Run this script with the install-shell command first."
        )

    LOCAL_SHELL.parent.mkdir(parents=True, exist_ok=True)
    temporary = LOCAL_SHELL.with_suffix(".download")
    print(f"Installing official aihubshell -> {LOCAL_SHELL.relative_to(PROJECT_ROOT)}")
    try:
        urllib.request.urlretrieve(AIHUBSHELL_URL, temporary)
        temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR)
        temporary.replace(LOCAL_SHELL)
    finally:
        temporary.unlink(missing_ok=True)
    return LOCAL_SHELL


def _run(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def fetch_tree(dataset_key: str) -> str:
    shell = ensure_aihubshell()
    result = _run(
        [str(shell), "-mode", "l", "-datasetkey", str(dataset_key)],
        cwd=PROJECT_ROOT,
        capture=True,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "unknown aihubshell error").strip()
        raise SystemExit(f"aihubshell list failed ({result.returncode}): {message}")
    return result.stdout or ""


def parse_tree(text: str) -> list[AIHubFile]:
    """Parse selectable file rows from current/legacy aihubshell tree output.

    AI Hub has used more than one indentation style. Matching leaf file names is
    more robust than relying on exact box-drawing indentation depth.
    """
    records: list[AIHubFile] = []
    seen_filekeys: set[str] = set()

    for raw_line in text.splitlines():
        line = ANSI_ESCAPE.sub("", raw_line.rstrip())
        leaf = re.sub(r"^[\s│├└─]+", "", line)
        file_match = FILE_INFO.match(leaf)
        if not file_match:
            continue

        filekey = file_match.group("filekey")
        if filekey in seen_filekeys:
            continue
        seen_filekeys.add(filekey)
        name = file_match.group("name").strip()
        records.append(
            AIHubFile(
                path=name,
                name=name,
                size=file_match.group("size").strip(),
                filekey=filekey,
            )
        )
    return records


def select_files(records: Iterable[AIHubFile], patterns: Sequence[str]) -> list[AIHubFile]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    if not compiled:
        return list(records)
    return [record for record in records if any(pattern.search(record.path) for pattern in compiled)]


def print_records(records: Sequence[AIHubFile]) -> None:
    if not records:
        print("No matching AI Hub files.")
        return
    for record in records:
        print(f"{record.filekey}\t{record.size}\t{record.path}")
    print(f"\nSelected: {len(records)} file(s)")
    print("filekeys=" + ",".join(record.filekey for record in records))


def download(
    dataset_key: str,
    destination: Path,
    *,
    filekeys: Sequence[str] = (),
    download_all: bool = False,
) -> None:
    if not filekeys and not download_all:
        raise SystemExit(
            "Refusing an implicit full-dataset download. Supply --filekey ... or pass --all explicitly."
        )

    shell = ensure_aihubshell()
    api_key = get_api_key()
    destination.mkdir(parents=True, exist_ok=True)

    args = [
        str(shell),
        "-mode",
        "d",
        "-datasetkey",
        str(dataset_key),
    ]
    if filekeys:
        args.extend(["-filekey", ",".join(filekeys)])
    args.extend(["-aihubapikey", api_key])

    print(f"AI Hub dataset {dataset_key} download -> {destination}")
    if filekeys:
        print("filekeys=" + ",".join(filekeys))
    else:
        print("scope=ALL (explicit --all)")
    print("API key is loaded from the environment/.env and is not printed by this script.")

    result = _run(args, cwd=destination, capture=False)
    if result.returncode != 0:
        raise SystemExit(f"aihubshell download failed with exit code {result.returncode}")


def build_parser(dataset_name: str, dataset_key: str, default_destination: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Selective AI Hub downloader for {dataset_name} (dataset {dataset_key})."
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("install-shell", help="Install official aihubshell into .cache/aihub/")

    tree_parser = subparsers.add_parser("tree", help="Show the current AI Hub file tree")
    tree_parser.add_argument("--save", type=Path, help="Also save raw tree output to a text file")

    plan_parser = subparsers.add_parser("plan", help="Select filekeys from the current file tree")
    plan_parser.add_argument(
        "--match",
        action="append",
        default=[],
        metavar="REGEX",
        help="Regex matched against AI Hub file names; may be repeated",
    )

    download_parser = subparsers.add_parser("download", help="Download explicit AI Hub filekeys")
    download_parser.add_argument("--filekey", action="append", default=[], help="AI Hub filekey; may be repeated")
    download_parser.add_argument("--all", action="store_true", help="Explicitly download the entire dataset")
    download_parser.add_argument("--dest", type=Path, default=default_destination)

    matching_parser = subparsers.add_parser(
        "download-matching", help="Resolve --match patterns against the live tree, then download those filekeys"
    )
    matching_parser.add_argument("--match", action="append", required=True, metavar="REGEX")
    matching_parser.add_argument("--dest", type=Path, default=default_destination)

    return parser


def run_dataset_cli(*, dataset_name: str, dataset_key: str, default_destination: Path) -> None:
    parser = build_parser(dataset_name, dataset_key, default_destination)
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "install-shell":
        print(ensure_aihubshell())
        return

    if args.command == "tree":
        tree = fetch_tree(dataset_key)
        print(tree, end="" if tree.endswith("\n") else "\n")
        if args.save:
            save_path = args.save.expanduser()
            if not save_path.is_absolute():
                save_path = PROJECT_ROOT / save_path
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(tree, encoding="utf-8")
            print(f"Saved tree: {save_path}", file=sys.stderr)
        return

    if args.command == "plan":
        records = parse_tree(fetch_tree(dataset_key))
        print_records(select_files(records, args.match))
        return

    if args.command == "download":
        destination = args.dest.expanduser()
        if not destination.is_absolute():
            destination = PROJECT_ROOT / destination
        download(dataset_key, destination, filekeys=args.filekey, download_all=args.all)
        return

    if args.command == "download-matching":
        records = parse_tree(fetch_tree(dataset_key))
        selected = select_files(records, args.match)
        if not selected:
            raise SystemExit("No files matched; nothing downloaded.")
        print_records(selected)
        destination = args.dest.expanduser()
        if not destination.is_absolute():
            destination = PROJECT_ROOT / destination
        download(dataset_key, destination, filekeys=[record.filekey for record in selected])
        return

    raise AssertionError(f"Unhandled command: {args.command}")
