#!/usr/bin/env python3
"""
PR Size Policy Checker for proj2-3.

Distinguishes between 'Review Core' (code, tests, specs, configs)
and 'Exceptions' (worklogs, experiment logs, lockfiles, machine artifacts).

Guidelines:
- Review Core <= 400 LOC: Recommended size.
- Review Core 401 ~ 800 LOC: Allowed if PR description documents the rationale
  and non-split justification.
- Review Core > 800 LOC: Blocked (must be split into logical/responsibility units).
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from typing import Dict, List, Tuple


# Exception patterns: Files that do not count towards Review Core
# Note: docs/experiments/** is NOT an exception by default.
# Specs, plans, methods, evaluation criteria, and reproduction procedures are Review Core.
# Only worklogs, lockfiles, machine artifacts, and raw result data are exceptions.
EXCEPTION_PATTERNS = [
    # Worklogs and operational daily logs
    "docs/worklogs/*",
    "docs/worklogs/**/*",
    # Raw benchmark result data and machine output (NOT markdown documentation)
    "local-results/*",
    "local-results/**/*",
    "evals/results/*",
    "evals/results/**/*",
    "*.jsonl",
    "*.csv",
    "*.tsv",
    # Lockfiles and dependency manifests
    "*lock*",
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    # Machine generated or minified artifacts
    "*.min.js",
    "*.min.css",
    "*.map",
]

# Specific prefixes or filenames that MUST ALWAYS be Review Core
ALWAYS_REVIEW_CORE_PATTERNS = [
    "docs/specs/*",
    "docs/specs/**/*",
    "docs/experiments/README.md",
    "EVAL_REPORT.md",
    "AGENTS.md",
]

REVIEW_CORE_RECOMMENDED_LIMIT = 400
REVIEW_CORE_HARD_LIMIT = 800


def is_exception_file(filepath: str) -> bool:
    norm_path = filepath.strip().replace("\\", "/")
    
    # 1. Check if explicitly designated as Review Core
    for pattern in ALWAYS_REVIEW_CORE_PATTERNS:
        if fnmatch.fnmatch(norm_path, pattern):
            return False
        if fnmatch.fnmatch(os.path.basename(norm_path), pattern):
            return False

    # 2. Check if matches exception patterns
    for pattern in EXCEPTION_PATTERNS:
        if fnmatch.fnmatch(norm_path, pattern):
            return True
        if fnmatch.fnmatch(os.path.basename(norm_path), pattern):
            return True

    # 3. Default is Review Core
    return False


def parse_numstat_line(line: str) -> Tuple[int, int, str] | None:
    parts = line.strip().split("\t")
    if len(parts) < 3:
        return None
    add_str, del_str, filepath = parts[0], parts[1], parts[2]
    # Binary files show '-' for additions and deletions
    if add_str == "-" or del_str == "-":
        return 0, 0, filepath
    try:
        return int(add_str), int(del_str), filepath
    except ValueError:
        return None


def get_git_diff_numstat(base: str, head: str) -> List[Tuple[int, int, str]]:
    cmd = ["git", "diff", "--numstat", f"{base}...{head}"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Error running git diff: {e.stderr}\n")
        raise
    
    file_stats = []
    for line in res.stdout.splitlines():
        stat = parse_numstat_line(line)
        if stat:
            file_stats.append(stat)
    return file_stats


def analyze_diff(file_stats: List[Tuple[int, int, str]]) -> Dict:
    core_add = 0
    core_del = 0
    except_add = 0
    except_del = 0

    core_files = []
    except_files = []

    for adds, dels, path in file_stats:
        total = adds + dels
        if is_exception_file(path):
            except_add += adds
            except_del += dels
            except_files.append((path, adds, dels, total))
        else:
            core_add += adds
            core_del += dels
            core_files.append((path, adds, dels, total))

    total_diff = (core_add + core_del) + (except_add + except_del)
    core_diff = core_add + core_del
    except_diff = except_add + except_del

    return {
        "total_diff": total_diff,
        "total_add": core_add + except_add,
        "total_del": core_del + except_del,
        "core_diff": core_diff,
        "core_add": core_add,
        "core_del": core_del,
        "except_diff": except_diff,
        "except_add": except_add,
        "except_del": except_del,
        "core_files": sorted(core_files, key=lambda x: x[3], reverse=True),
        "except_files": sorted(except_files, key=lambda x: x[3], reverse=True),
    }


def check_pr_description_for_rationale(body: str) -> Tuple[bool, str]:
    """
    Check if the PR body provides rationale when review core > 400 LOC.
    Looks for non-empty explanations in rationale or justification sections.
    """
    if not body or not body.strip():
        return False, "PR description is completely empty."

    # Search for common indicators/sections
    # e.g., '초과', '사유', '이유', 'rationale', 'justification', 'review-size'
    keywords = ["사유", "이유", "rationale", "justification", "기준 초과", "분리하지 않은"]
    body_lower = body.lower()
    found_kw = [kw for kw in keywords if kw in body_lower]

    if not found_kw:
        return False, "PR description does not mention any rationale or justification keywords ('사유', '이유', 'rationale', etc.)."

    # Ensure it's not just template placeholder comments
    # Strip html comments: <!-- ... -->
    clean_body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).strip()
    if len(clean_body) < 30:
        return False, "PR description is too short after removing markdown comments."

    return True, "Rationale section found."


def evaluate_policy(analysis: Dict, pr_body: str | None = None) -> Tuple[bool, List[str]]:
    passed = True
    messages = []

    core_diff = analysis["core_diff"]
    total_diff = analysis["total_diff"]

    messages.append(f"Diff Summary:")
    messages.append(f"  - Total Diff: {total_diff} lines (+{analysis['total_add']} / -{analysis['total_del']})")
    messages.append(f"  - Review Core Diff: {core_diff} lines (+{analysis['core_add']} / -{analysis['core_del']})")
    messages.append(f"  - Exception Diff: {analysis['except_diff']} lines (+{analysis['except_add']} / -{analysis['except_del']})")

    if analysis["core_files"]:
        messages.append("  Top Review Core Files:")
        for path, adds, dels, tot in analysis["core_files"][:5]:
            messages.append(f"    * {path}: +{adds}/-{dels} ({tot} lines)")

    if analysis["except_files"]:
        messages.append("  Top Exception Files:")
        for path, adds, dels, tot in analysis["except_files"][:5]:
            messages.append(f"    * {path}: +{adds}/-{dels} ({tot} lines)")

    # Policy evaluation
    if core_diff > REVIEW_CORE_HARD_LIMIT:
        passed = False
        messages.append(
            f"\n[POLICY VIOLATION] Review Core size is {core_diff} lines, which exceeds the hard limit of {REVIEW_CORE_HARD_LIMIT} lines.\n"
            f"Please split this PR into smaller, responsibility-focused PRs."
        )
    elif core_diff > REVIEW_CORE_RECOMMENDED_LIMIT:
        messages.append(
            f"\n[NOTICE] Review Core size is {core_diff} lines (exceeds recommended guideline of {REVIEW_CORE_RECOMMENDED_LIMIT} lines)."
        )
        if pr_body is not None:
            has_rationale, reason = check_pr_description_for_rationale(pr_body)
            if not has_rationale:
                passed = False
                messages.append(
                    f"[POLICY VIOLATION] Review Core exceeds {REVIEW_CORE_RECOMMENDED_LIMIT} lines, but PR description lacks documented rationale: {reason}\n"
                    f"Please document the rationale and non-split justification in your PR description."
                )
            else:
                messages.append(f"[PASS] Documented rationale found in PR description: {reason}")
        else:
            messages.append(
                f"[ADVICE] Ensure your PR description documents the rationale and why this is not split."
            )
    else:
        messages.append(
            f"\n[PASS] Review Core size ({core_diff} lines) is within recommended limit ({REVIEW_CORE_RECOMMENDED_LIMIT} lines)."
        )

    return passed, messages


def main():
    parser = argparse.ArgumentParser(description="Check PR size and review core policy.")
    parser.add_argument("--base", default="origin/main", help="Base git ref (default: origin/main)")
    parser.add_argument("--head", default="HEAD", help="Head git ref (default: HEAD)")
    parser.add_argument("--pr-body", default=None, help="PR description text (or path to file if prefixed with @)")
    parser.add_argument("--pr-body-file", default=None, help="Path to file containing PR description")

    args = parser.parse_args()

    pr_body = None
    if args.pr_body_file and os.path.exists(args.pr_body_file):
        with open(args.pr_body_file, "r", encoding="utf-8") as f:
            pr_body = f.read()
    elif args.pr_body:
        if args.pr_body.startswith("@") and os.path.exists(args.pr_body[1:]):
            with open(args.pr_body[1:], "r", encoding="utf-8") as f:
                pr_body = f.read()
        else:
            pr_body = args.pr_body

    file_stats = get_git_diff_numstat(args.base, args.head)
    analysis = analyze_diff(file_stats)
    passed, messages = evaluate_policy(analysis, pr_body=pr_body)

    for msg in messages:
        print(msg)

    if not passed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

