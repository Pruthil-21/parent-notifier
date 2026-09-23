import io
import re
import zipfile

import pytest

from parent_notifier.services.imports import sheet_reader
from parent_notifier.services.imports.sheet_reader import SheetReadError, read_sheet
from tests.factories.workbooks import make_csv, make_xlsx, sheet_rows


def test_xlsx_is_read_as_text():
    grid = read_sheet("sem4.xlsx", make_xlsx())
    assert grid[0][:2] == ["Enrollment No", "Student Name"]
    assert grid[1][4] == "Theory=86,Practical=92,Marks=16"


def test_long_numbers_stay_whole():
    rows = sheet_rows(rows=[[230120107001, "Avi Shah", "Mehul Shah", 9000000101.0, "", ""]])
    grid = read_sheet("sem4.xlsx", make_xlsx(rows))
    assert grid[1][:4] == ["230120107001", "Avi Shah", "Mehul Shah", "9000000101"]


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1252"])
def test_csv_in_common_encodings(encoding):
    rows = sheet_rows(rows=[["23CE001", "Zoë Shah", "Mehul Shah", "9000000101", "", ""]])
    grid = read_sheet("sem4.CSV", make_csv(rows, encoding))
    assert grid[1][1] == "Zoë Shah"


def test_blank_rows_keep_row_numbers_and_trailing_ones_go():
    grid = read_sheet("sem4.csv", b"a,b\r\n,\r\nc,d\r\n,\r\n,\r\n")
    assert grid == [["a", "b"], [], ["c", "d"]]


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("marks.xls", "Old .xls files cannot be read"),
        ("marks.pdf", "Upload an Excel (.xlsx) or CSV (.csv) file"),
        ("marks", "Upload an Excel (.xlsx) or CSV (.csv) file"),
    ],
)
def test_other_file_types_are_refused(name, message):
    with pytest.raises(SheetReadError, match=re.escape(message)):
        read_sheet(name, make_xlsx())


def test_file_that_is_not_really_xlsx_is_refused():
    with pytest.raises(SheetReadError, match="could not be read"):
        read_sheet("sem4.xlsx", b"not a workbook")
    with pytest.raises(SheetReadError, match="could not be read"):
        read_sheet("sem4.xlsx", _zip({"hello.txt": b"hi"}))


def test_zip_bomb_is_refused_before_it_is_unpacked():
    with pytest.raises(SheetReadError, match="too large to read"):
        read_sheet("sem4.xlsx", _zip({"xl/worksheets/sheet1.xml": b"0" * 5_000_000}))


def test_xml_entities_are_refused():
    with zipfile.ZipFile(io.BytesIO(make_xlsx())) as source:
        parts = {name: source.read(name) for name in source.namelist()}
    sheet = parts["xl/worksheets/sheet1.xml"].decode()
    doctype = '<!DOCTYPE worksheet [<!ENTITY e "boom">]>'
    declaration = re.match(r"<\?xml[^>]*\?>", sheet)
    cut = declaration.end() if declaration else 0
    parts["xl/worksheets/sheet1.xml"] = (sheet[:cut] + doctype + sheet[cut:]).encode()
    with pytest.raises(SheetReadError, match="could not be read"):
        read_sheet("sem4.xlsx", _zip(parts))


def test_damaged_rows_are_refused():
    with zipfile.ZipFile(io.BytesIO(make_xlsx())) as source:
        parts = {name: source.read(name) for name in source.namelist()}
    sheet = parts["xl/worksheets/sheet1.xml"]
    parts["xl/worksheets/sheet1.xml"] = sheet[: len(sheet) // 2]
    with pytest.raises(SheetReadError, match="could not be read"):
        read_sheet("sem4.xlsx", _zip(parts))


def test_row_and_column_limits(monkeypatch):
    monkeypatch.setattr(sheet_reader, "MAX_ROWS", 3)
    too_many = "\r\n".join(f"23CE{n:03},x" for n in range(20)).encode()
    with pytest.raises(SheetReadError, match="more than 3 students"):
        read_sheet("sem4.csv", too_many)
    wide = ",".join(["x"] * (sheet_reader.MAX_COLUMNS + 1)).encode()
    with pytest.raises(SheetReadError, match="more than 64 columns"):
        read_sheet("sem4.csv", wide)


def _zip(parts: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    return buffer.getvalue()
