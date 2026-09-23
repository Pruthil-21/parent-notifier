"""Listing the files a check should look at, and reporting what it found."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    level: str  # "warning" or "error"
    message: str


def tracked_files(root: Path) -> list[str]:
    """Files in the git index, as POSIX paths relative to the repository root.

    Staged files count, so pre-commit sees a new file before its first commit.
    """
    result = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    )
    return result.stdout.splitlines()


def report(findings: list[Finding]) -> int:
    """Print every finding and return the process exit code."""
    for finding in findings:
        print(f"{finding.level}: {finding.message}")
    return 1 if any(f.level == "error" for f in findings) else 0
