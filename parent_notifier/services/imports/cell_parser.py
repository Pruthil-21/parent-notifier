"""One subject cell of a sheet, such as "Theory=86,Practical=92,Marks=16".

The reader is forgiving about how people type (";", "|" or new lines between parts, ":"
for "=", "82%", "16/20", short keys, any case) and strict about the numbers themselves.
"""

import re
from dataclasses import dataclass


class CellError(ValueError):
    """A cell that cannot be read; the message says how to fix it."""


@dataclass(frozen=True)
class SubjectCell:
    theory: float | None = None
    practical: float | None = None
    marks: float | None = None
    absent: bool = False

    @property
    def is_empty(self) -> bool:
        return self == SubjectCell()


_PARTS = re.compile(r"[,;|\r\n]+")
_KEY_VALUE = re.compile(r"^\s*([^=:]+?)\s*[=:]\s*(.*?)\s*$")
_NUMBER = re.compile(r"^(\d+(?:\.\d+)?)\s*(?:(%)|/\s*(\d+(?:\.\d+)?))?$")
_KEYS = {
    "theory": "theory",
    "th": "theory",
    "practical": "practical",
    "prac": "practical",
    "pr": "practical",
    "marks": "marks",
    "mark": "marks",
    "mid": "marks",
    "midsem": "marks",
}
LABELS = {"theory": "Theory", "practical": "Practical", "marks": "Marks"}
_BLANK = {"", "-", "--", "na", "n/a", "nil"}
_ABSENT = {"ab", "abs", "absent"}


def _key(raw: str) -> str:
    key = _KEYS.get(re.sub(r"[\s.\-_]", "", raw.lower()))
    if key is None:
        raise CellError(f'Unknown part "{raw}". Use Theory, Practical and Marks')
    return key


def _split(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for part in _PARTS.split(text):
        if not part.strip():
            continue
        match = _KEY_VALUE.match(part)
        if match is None:
            raise CellError(f'"{part.strip()}" is not in the form Theory=86')
        key = _key(match[1])
        if key in values:
            raise CellError(f"{LABELS[key]} appears twice")
        values[key] = match[2]
    return values


def _percent(raw: str | None, label: str) -> float | None:
    if raw is None or raw.lower() in _BLANK:
        return None
    match = _NUMBER.match(raw)
    if match is None or match[3] is not None or float(match[1]) > 100:
        raise CellError(f"{label} must be a percentage from 0 to 100, like {label}=82")
    return float(match[1])


def _marks(raw: str | None, midsem_max: int) -> tuple[float | None, bool]:
    if raw is None or raw.lower() in _BLANK:
        return None, False
    if raw.lower() in _ABSENT:
        return None, True
    match = _NUMBER.match(raw)
    if match is None or match[2]:
        raise CellError(f"Marks must be a number from 0 to {midsem_max}, or AB if absent")
    if match[3] is not None and float(match[3]) != midsem_max:
        raise CellError(f"Marks must be out of {midsem_max} for this class")
    if float(match[1]) > midsem_max:
        raise CellError(f"Marks must be from 0 to {midsem_max}")
    return float(match[1]), False


def parse_cell(text: object, midsem_max: int) -> SubjectCell:
    """Read a cell; a blank cell means no data yet for that subject."""
    if text is None or not str(text).strip():
        return SubjectCell()
    values = _split(str(text))
    marks, absent = _marks(values.get("marks"), midsem_max)
    return SubjectCell(
        theory=_percent(values.get("theory"), "Theory"),
        practical=_percent(values.get("practical"), "Practical"),
        marks=marks,
        absent=absent,
    )


def _number(value: float) -> str:
    return f"{value:g}"


def format_cell(cell: SubjectCell) -> str:
    """The cell as a mentor would type it, for pre-filled sheets. Missing parts are left
    out, so the result parses back to the same cell."""
    parts = []
    if cell.theory is not None:
        parts.append(f"Theory={_number(cell.theory)}")
    if cell.practical is not None:
        parts.append(f"Practical={_number(cell.practical)}")
    if cell.absent:
        parts.append("Marks=AB")
    elif cell.marks is not None:
        parts.append(f"Marks={_number(cell.marks)}")
    return ",".join(parts)
