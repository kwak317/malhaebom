#!/usr/bin/env python3
"""Check links in maintained entry-point documents without rewriting historical logs."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ENTRY_DOCS = (
    "README.md",
    "docs/README.md",
    "docs/PROJECT_OVERVIEW.md",
    "docs/REQUIREMENTS.md",
    "docs/CURRENT_STATE.md",
    "docs/PYTHON_ENVIRONMENT.md",
    "docs/project2-checkpoint-work-cards.md",
)
# Only these maintained entry points are expected to use *current* Skill paths.
SKILL_PATH_DOCS = frozenset({"README.md", "docs/project2-checkpoint-work-cards.md"})
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
INLINE_SKILL_PATH = re.compile(r"`(skills/[A-Za-z0-9_./-]+\.(?:md|json))`")
# Individual workstation paths do not belong in maintained project guidance.
# Keep generic environment commands and historical worklogs outside this check.
PERSONAL_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"
    r"|/(?:home|Users)/[^/\s]+/"
    r"|/mnt/[a-z]/Users/[^/\s]+/",
)


def check_document(
    path: Path,
    root: Path,
    *,
    check_skills: bool = False,
    check_personal_paths: bool = False,
) -> list[str]:
    """Return location-only diagnostics; never emit file contents."""
    failures: list[str] = []
    if not path.is_file():
        return [f"{path.relative_to(root)}: document missing"]
    inside_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith(("~~~", "```")):
            inside_fence = not inside_fence
            continue
        if inside_fence:
            continue
        if check_personal_paths and PERSONAL_ABSOLUTE_PATH.search(line):
            failures.append(
                f"{path.relative_to(root)}:{number}: personal absolute path in guidance"
            )
        targets = [match.group(1) for match in MARKDOWN_LINK.finditer(line)]
        if check_skills:
            targets += [match.group(1) for match in INLINE_SKILL_PATH.finditer(line)]
        for target in targets:
            target = target.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            resolved = (root / target if target.startswith("skills/") else path.parent / target).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                failures.append(f"{path.relative_to(root)}:{number}: unresolved {target}")
    return failures


def check_repository(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    for name in ENTRY_DOCS:
        findings.extend(
            check_document(
                root / name,
                root,
                check_skills=name in SKILL_PATH_DOCS,
                check_personal_paths=True,
            )
        )
    return findings


def main() -> int:
    findings = check_repository()
    for finding in findings:
        print(finding)
    if findings:
        return 1
    print(f"Documentation references: OK ({len(ENTRY_DOCS)} maintained documents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
