"""Opening an uploaded .xlsx or .csv file as a grid of strings, within safe limits.

An .xlsx file is a zip archive, so its unpacked size and compression ratio are checked
before openpyxl reads it (zip bombs). openpyxl parses the XML through defusedxml, which
refuses entity tricks. Only the first worksheet is read, as plain values, never formulas.
"""

import csv
import io
import zipfile
from pathlib import PurePath

MAX_ROWS = 1000
MAX_COLUMNS = 64
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
_UNREADABLE = "The file could not be read. Save it again as .xlsx and retry"


class SheetReadError(ValueError):
    """The file cannot be read; the message says what to do instead."""


def read_sheet(filename: str, data: bytes) -> list[list[str]]:
    extension = PurePath(filename).suffix.lower()
    if extension == ".xlsx":
        return _limited(_xlsx_rows(data))
    if extension == ".csv":
        return _limited(_csv_rows(data))
    if extension == ".xls":
        raise SheetReadError("Old .xls files cannot be read. Open it in Excel and save as .xlsx")
    raise SheetReadError("Upload an Excel (.xlsx) or CSV (.csv) file")


def _text(value: object) -> str:
    """Excel stores long numbers such as enrollment numbers as floats; show them whole."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _check_archive(data: bytes) -> None:
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise SheetReadError(_UNREADABLE)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
    unpacked = sum(entry.file_size for entry in entries)
    packed = sum(entry.compress_size for entry in entries) or 1
    if unpacked > MAX_UNPACKED_BYTES or unpacked / packed > MAX_COMPRESSION_RATIO:
        raise SheetReadError("The file is too large to read. Keep one semester per sheet")


def _xlsx_rows(data: bytes):
    # Imported here, not at the top, so starting the app doesn't wait for openpyxl.
    from openpyxl import load_workbook

    _check_archive(data)
    # read_only parses rows lazily, so a damaged sheet can fail while rows are read, not
    # only when the file is opened. openpyxl raises many different types for that.
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        raise SheetReadError(_UNREADABLE) from None
    try:
        for row in workbook.worksheets[0].iter_rows(max_col=MAX_COLUMNS + 1, values_only=True):
            yield [_text(value) for value in row]
    except Exception:
        raise SheetReadError(_UNREADABLE) from None
    finally:
        workbook.close()


def _csv_rows(data: bytes):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # CSV files saved by Excel on Windows usually use this code page.
        text = data.decode("cp1252", errors="replace")
    for row in csv.reader(io.StringIO(text)):
        yield [cell.strip() for cell in row[: MAX_COLUMNS + 1]]


def _limited(rows) -> list[list[str]]:
    """Keep non-blank rows, and stop as soon as a limit is passed rather than reading on."""
    grid: list[list[str]] = []
    for row in rows:
        if len(row) > MAX_COLUMNS and any(row[MAX_COLUMNS:]):
            raise SheetReadError(f"The sheet has more than {MAX_COLUMNS} columns")
        if not any(row):
            grid.append([])
            continue
        grid.append(row[:MAX_COLUMNS])
        # A few rows of headings and titles are allowed on top of the student rows.
        if sum(1 for line in grid if line) > MAX_ROWS + 10:
            raise SheetReadError(f"The sheet has more than {MAX_ROWS} students")
    while grid and not grid[-1]:
        grid.pop()
    return grid
