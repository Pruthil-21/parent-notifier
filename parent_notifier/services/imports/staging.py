"""Holding a parsed sheet between the review page and Confirm.

Each staged import is a JSON file in the instance folder named by a random token. The
token is checked against a strict pattern before any path is built, the file records
which mentor, class and semester it belongs to, and it is never served back.
"""

import json
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from parent_notifier.services.imports.cell_parser import SubjectCell
from parent_notifier.services.imports.sheet_parser import ParsedSheet, SheetRow
from parent_notifier.services.shared import clock

MAX_AGE = timedelta(hours=24)
_TOKEN = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True)
class Owner:
    mentor_id: int
    class_id: int
    semester_id: int


@dataclass
class StagedImport:
    token: str
    owner: Owner
    filename: str
    sheet: ParsedSheet


def stage(directory: Path, owner: Owner, filename: str, sheet: ParsedSheet) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    purge_old(directory)
    token = secrets.token_hex(16)
    payload = {
        "owner": asdict(owner),
        "filename": filename,
        "staged_at": clock.now().isoformat(),
        "sheet": asdict(sheet),
    }
    (directory / f"{token}.json").write_text(json.dumps(payload), encoding="utf-8")
    return token


def _path(directory: Path, token: str) -> Path | None:
    return directory / f"{token}.json" if _TOKEN.fullmatch(token or "") else None


def load(directory: Path, token: str, owner: Owner) -> StagedImport | None:
    """The staged import, only for the same mentor, class and semester and while fresh."""
    path = _path(directory, token)
    if path is None or not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    staged_at = datetime.fromisoformat(payload["staged_at"])
    if Owner(**payload["owner"]) != owner or clock.now() - staged_at > MAX_AGE:
        return None
    return StagedImport(token, owner, payload["filename"], _sheet(payload["sheet"]))


def discard(directory: Path, token: str) -> None:
    path = _path(directory, token)
    if path is not None:
        path.unlink(missing_ok=True)


def purge_old(directory: Path) -> None:
    cutoff = (clock.now() - MAX_AGE).timestamp()
    for path in directory.glob("*.json"):
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)


def _sheet(data: dict) -> ParsedSheet:
    rows = [
        SheetRow(**(row | {"cells": {k: SubjectCell(**v) for k, v in row["cells"].items()}}))
        for row in data["rows"]
    ]
    return ParsedSheet(**(data | {"rows": rows}))
