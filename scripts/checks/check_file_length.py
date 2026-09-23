"""Warn when a source file passes 200 lines and fail when it passes 500.

Usage, from the repository root:
    python -m scripts.checks.check_file_length [FILE ...]

With no arguments every tracked file is checked.
"""

import sys
from pathlib import Path

from scripts.checks.repo_scan import Finding, report, tracked_files

SOFT_LIMIT = 200
HARD_LIMIT = 500
CHECKED_SUFFIXES = {".py", ".html", ".css", ".js", ".sql", ".txt"}
GENERATED_PREFIXES = ("migrations/versions/",)


def is_checked(path: str) -> bool:
    return Path(path).suffix in CHECKED_SUFFIXES and not path.startswith(GENERATED_PREFIXES)


def count_lines(file: Path) -> int:
    with file.open("rb") as handle:
        return sum(1 for _ in handle)


def check(paths: list[str], root: Path) -> list[Finding]:
    findings = []
    for path in paths:
        file = root / path
        if not is_checked(path) or not file.is_file():
            continue
        lines = count_lines(file)
        if lines > HARD_LIMIT:
            message = f"{path} has {lines} lines; split it by responsibility (limit {HARD_LIMIT})"
            findings.append(Finding("error", message))
        elif lines > SOFT_LIMIT:
            message = f"{path} has {lines} lines; consider splitting (target {SOFT_LIMIT})"
            findings.append(Finding("warning", message))
    return findings


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path.cwd()
    paths = [Path(arg).as_posix() for arg in args] or tracked_files(root)
    return report(check(paths, root))


if __name__ == "__main__":
    sys.exit(main())
