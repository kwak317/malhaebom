from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import venv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENV_DIR = PROJECT_ROOT / ".venv"
PYTORCH_INDEX = "https://download.pytorch.org/whl/cu128"
PYTORCH_VERSION = "2.8.0"

# Pinned dev tools
NODE_VERSION = "v22.14.0"
NODE_TARBALL = f"node-{NODE_VERSION}-linux-x64.tar.xz"
NODE_URL = f"https://nodejs.org/dist/{NODE_VERSION}/{NODE_TARBALL}"
NODE_SHA256 = "69b09dba5c8dcb05c4e4273a4340db1005abeafe3927efda2bc5b249e80437ec"

SUPABASE_VERSION = "v2.117.0"
SUPABASE_TARBALL = "supabase_2.117.0_linux_amd64.tar.gz"
SUPABASE_URL = f"https://github.com/supabase/cli/releases/download/{SUPABASE_VERSION}/{SUPABASE_TARBALL}"
SUPABASE_SHA256 = "69c05f85b9e47ee706d30f1a6ca8a526b4e337bfd12c7ef1ef522d24e7280d24"


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def ensure_python_version() -> None:
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(
            f"Python 3.12 is required; current interpreter is {sys.version.split()[0]}"
        )


def venv_python(venv_dir: Path | None = None) -> Path:
    base = venv_dir or VENV_DIR
    if os.name == "nt":
        return base / "Scripts" / "python.exe"
    return base / "bin" / "python"


def create_venv(venv_dir: Path | None = None) -> Path:
    ensure_python_version()
    target_dir = venv_dir or VENV_DIR
    python = venv_python(target_dir)
    if python.exists():
        pip_ok = subprocess.run(
            [str(python), "-m", "pip", "--version"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
        if pip_ok:
            print(f"Reusing existing {target_dir}")
            return python
        shutil.rmtree(target_dir)

    uv = shutil.which("uv")
    if uv:
        run(uv, "venv", "--python", "3.12", str(target_dir))
    else:
        virtualenv = shutil.which("virtualenv")
        if virtualenv:
            run(virtualenv, "--python", sys.executable, str(target_dir))
        else:
            venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(target_dir)

    python = venv_python(target_dir)
    if not python.exists():
        raise SystemExit(f"Failed to create {target_dir}")
    return python


def install_dependencies(python: Path, *, with_question_tts: bool) -> None:
    py = str(python)
    run(py, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
    run(
        py,
        "-m",
        "pip",
        "install",
        f"torch=={PYTORCH_VERSION}",
        f"torchaudio=={PYTORCH_VERSION}",
        "--index-url",
        PYTORCH_INDEX,
    )
    run(py, "-m", "pip", "install", "-r", "backend/requirements.txt")
    if with_question_tts:
        run(py, "-m", "pip", "install", "-r", "backend/requirements-question-tts.txt")
    run(py, "-m", "pip", "check")


def check_linux_x86_64() -> None:
    sys_name = platform.system().lower()
    machine = platform.machine().lower()
    if sys_name != "linux" or machine not in {"x86_64", "amd64"}:
        raise SystemExit(
            f"Dev tools (--with-dev-tools) are currently supported on Linux x86_64 only. "
            f"Detected: system='{platform.system()}', machine='{platform.machine()}'"
        )


def _verify_sha256(file_path: Path, expected_hash: str) -> None:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    if actual_hash.lower() != expected_hash.lower():
        raise ValueError(
            f"Checksum mismatch for {file_path.name}: "
            f"expected {expected_hash}, got {actual_hash}"
        )


def _safe_extract(tar: tarfile.TarFile, target_dir: Path) -> None:
    target_dir = target_dir.resolve()
    for member in tar.getmembers():
        # Reject absolute paths or paths containing .. components directly in name
        member_name = member.name
        if os.path.isabs(member_name) or ".." in Path(member_name).parts:
            raise RuntimeError(f"Attempted path traversal in tar extraction: {member.name}")

        member_path = (target_dir / member_name).resolve()
        if not member_path.is_relative_to(target_dir):
            raise RuntimeError(f"Attempted path traversal in tar extraction: {member.name}")

        # Check symlinks and hardlinks: target must stay strictly within target_dir
        if member.issym() or member.islnk():
            link_target = Path(member.linkname)
            if link_target.is_absolute():
                resolved_link = link_target.resolve()
            else:
                resolved_link = (member_path.parent / link_target).resolve()
            if not resolved_link.is_relative_to(target_dir):
                raise RuntimeError(
                    f"Unsafe link target outside extraction directory: {member.name} -> {member.linkname}"
                )

    tar.extractall(target_dir)


def _download_and_extract_atomic(
    url: str,
    expected_sha256: str,
    dest_dir: Path,
    tarball_name: str,
    strip_single_top_dir: bool = False,
) -> None:
    if dest_dir.exists():
        return

    downloads_dir = dest_dir.parent / ".downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    archive_path = downloads_dir / tarball_name

    print(f"Downloading {url} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "proj2-3-bootstrap"})
    with urllib.request.urlopen(req) as resp, open(archive_path, "wb") as out_f:
        shutil.copyfileobj(resp, out_f)

    print(f"Verifying checksum for {tarball_name} ...", flush=True)
    _verify_sha256(archive_path, expected_sha256)

    tmp_dir = dest_dir.parent / f".tmp_{dest_dir.name}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting {tarball_name} ...", flush=True)
    mode = "r:xz" if archive_path.name.endswith(".tar.xz") else "r:gz"
    with tarfile.open(archive_path, mode=mode) as tar:
        _safe_extract(tar, tmp_dir)

    if strip_single_top_dir:
        entries = list(tmp_dir.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            top_dir = entries[0]
            for child in top_dir.iterdir():
                child.rename(tmp_dir / child.name)
            top_dir.rmdir()

    tmp_dir.rename(dest_dir)
    if archive_path.exists():
        archive_path.unlink()


def _ensure_symlink(link_path: Path, target_path: Path) -> None:
    if link_path.is_symlink() or link_path.exists():
        link_path.unlink()
    rel_target = os.path.relpath(target_path, link_path.parent)
    link_path.symlink_to(rel_target)


def install_dev_tools(venv_dir: Path | None = None) -> None:
    check_linux_x86_64()
    target_dir = venv_dir or VENV_DIR
    tools_dir = target_dir / "tools"
    bin_dir = target_dir / "bin"
    tools_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)

    # 1. Node.js
    node_extracted_dir = tools_dir / f"node-{NODE_VERSION}-linux-x64"
    _download_and_extract_atomic(
        url=NODE_URL,
        expected_sha256=NODE_SHA256,
        dest_dir=node_extracted_dir,
        tarball_name=NODE_TARBALL,
        strip_single_top_dir=True,
    )
    for cmd in ["node", "npm", "npx"]:
        src_bin = node_extracted_dir / "bin" / cmd
        dst_bin = bin_dir / cmd
        if not src_bin.exists():
            raise RuntimeError(f"Missing node binary at {src_bin}")
        _ensure_symlink(dst_bin, src_bin)

    # 2. Supabase CLI
    supabase_extracted_dir = tools_dir / f"supabase-{SUPABASE_VERSION}"
    _download_and_extract_atomic(
        url=SUPABASE_URL,
        expected_sha256=SUPABASE_SHA256,
        dest_dir=supabase_extracted_dir,
        tarball_name=SUPABASE_TARBALL,
        strip_single_top_dir=False,
    )
    src_supabase = supabase_extracted_dir / "supabase"
    dst_supabase = bin_dir / "supabase"
    if not src_supabase.exists():
        raise RuntimeError(f"Missing supabase binary at {src_supabase}")
    src_supabase.chmod(0o755)
    _ensure_symlink(dst_supabase, src_supabase)

    # 3. Verification of installed dev tools (with bin_dir prepended to PATH)
    print("Verifying installed dev tools ...", flush=True)
    env = dict(os.environ, PATH=f"{bin_dir}:{os.environ.get('PATH', '')}")

    # node
    res_node = subprocess.run(
        [str(bin_dir / "node"), "--version"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    actual_node = res_node.stdout.strip()
    if actual_node != NODE_VERSION:
        raise RuntimeError(f"Node version mismatch: expected {NODE_VERSION}, got {actual_node}")

    # npm
    res_npm = subprocess.run(
        [str(bin_dir / "npm"), "--version"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    print(f"Verified node {actual_node}, npm {res_npm.stdout.strip()}", flush=True)

    # npx
    res_npx = subprocess.run(
        [str(bin_dir / "npx"), "--version"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    print(f"Verified npx {res_npx.stdout.strip()}", flush=True)

    # supabase
    res_supa = subprocess.run(
        [str(bin_dir / "supabase"), "--version"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    actual_supa = res_supa.stdout.strip()
    if SUPABASE_VERSION.lstrip("v") not in actual_supa:
        raise RuntimeError(
            f"Supabase version mismatch: expected {SUPABASE_VERSION}, got {actual_supa}"
        )
    print(f"Verified supabase CLI {actual_supa}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the project-local Python 3.12 backend/runtime environment."
    )
    parser.add_argument(
        "--create-only",
        action="store_true",
        help="Create .venv without installing Python packages.",
    )
    parser.add_argument(
        "--with-question-tts",
        action="store_true",
        help=(
            "Also install the in-process question TTS dependencies. "
            "The transferred standalone TTS runtime remains .venvs/tts-runtime."
        ),
    )
    parser.add_argument(
        "--with-dev-tools",
        action="store_true",
        help=(
            "Install project-local Node.js (node/npm/npx) and Supabase CLI into .venv/tools "
            "and symlink them to .venv/bin."
        ),
    )
    args = parser.parse_args()

    python = create_venv()
    if not args.create_only:
        install_dependencies(python, with_question_tts=args.with_question_tts)

    if args.with_dev_tools:
        install_dev_tools()

    print(f"venv: {VENV_DIR}")
    print(f"python: {python}")
    if os.name != "nt":
        print("activate: source .venv/bin/activate")


if __name__ == "__main__":
    main()
