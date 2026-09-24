"""Holding a parsed sheet between the review page and Confirm.

Each staged sheet is a database row keyed by a random token. It records which mentor,
class and semester it belongs to, loads only for that same owner while fresh, and is
never served back.
"""

import re
import secrets
from dataclasses import asdict, dataclass
from datetime import timedelta

from sqlalchemy import delete

from parent_notifier.core.extensions import db
from parent_notifier.models.imports import StagedSheet
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


def stage(owner: Owner, filename: str, sheet: ParsedSheet) -> str:
    purge_old()
    token = secrets.token_hex(16)
    db.session.add(
        StagedSheet(token=token, filename=filename, sheet=asdict(sheet), **asdict(owner))
    )
    db.session.commit()
    return token


def _find(token: str) -> StagedSheet | None:
    return db.session.get(StagedSheet, token) if _TOKEN.fullmatch(token or "") else None


def load(token: str, owner: Owner) -> StagedImport | None:
    """The staged import, only for the same mentor, class and semester and while fresh."""
    row = _find(token)
    if row is None:
        return None
    found = Owner(row.mentor_id, row.class_id, row.semester_id)
    if found != owner or clock.now() - row.created_at > MAX_AGE:
        return None
    return StagedImport(token, owner, row.filename, _sheet(row.sheet))


def discard(token: str) -> None:
    row = _find(token)
    if row is not None:
        db.session.delete(row)
        db.session.commit()


def purge_old() -> None:
    cutoff = clock.now() - MAX_AGE
    db.session.execute(delete(StagedSheet).where(StagedSheet.created_at < cutoff))
    db.session.commit()


def _sheet(data: dict) -> ParsedSheet:
    rows = [
        SheetRow(**(row | {"cells": {k: SubjectCell(**v) for k, v in row["cells"].items()}}))
        for row in data["rows"]
    ]
    return ParsedSheet(**(data | {"rows": rows}))
