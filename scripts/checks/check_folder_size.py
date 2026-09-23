"""Keep folders small and file names specific.

Warns when a folder holds 9 files and fails at 12, not counting __init__.py,
LICENSE or README.md. Also fails on catch-all names such as utils.py. The
repository root (tool configuration), generated migrations and the icon asset
set are exempt.

Usage, from the repository root:
    python -m scripts.checks.check_folder_size
"""

import sys
from collections import Counter
from pathlib import Path, PurePosixPath

from scripts.checks.repo_scan import Finding, report, tracked_files

WARN_AT = 9
FAIL_AT = 12
NOT_COUNTED = {"__init__.py", "LICENSE", "README.md"}
EXEMPT_FOLDERS = {".", "migrations/versions", "parent_notifier/static/icons/fluent"}
CATCH_ALL_STEMS = {"utils", "helpers", "misc", "common", "stuff"}


def files_per_folder(paths: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in paths:
        pure = PurePosixPath(path)
        if pure.name not in NOT_COUNTED:
            counts[str(pure.parent)] += 1
    return counts


def check(paths: list[str]) -> list[Finding]:
    findings = []
    for folder, count in sorted(files_per_folder(paths).items()):
        if folder in EXEMPT_FOLDERS:
            continue
        if count >= FAIL_AT:
            limit = FAIL_AT - 1
            message = f"{folder}/ holds {count} files; group them into subfolders (limit {limit})"
            findings.append(Finding("error", message))
        elif count >= WARN_AT:
            message = f"{folder}/ holds {count} files; plan subfolders (target {WARN_AT - 1})"
            findings.append(Finding("warning", message))
    for path in paths:
        if PurePosixPath(path).stem.lower() in CATCH_ALL_STEMS:
            message = f"{path} is a catch-all name; name the file after what it does"
            findings.append(Finding("error", message))
    return findings


def main() -> int:
    return report(check(tracked_files(Path.cwd())))


if __name__ == "__main__":
    sys.exit(main())
