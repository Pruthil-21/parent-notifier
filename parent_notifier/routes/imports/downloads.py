"""Downloading the sheet format and a pre-filled semester sheet."""

import io

from flask import Blueprint, send_file
from flask_login import login_required
from werkzeug.utils import secure_filename

from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.services.exports.prefilled_sheet import prefilled_sheet
from parent_notifier.services.exports.sample_format import sample_format

bp = Blueprint("downloads", __name__)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(data: bytes, filename: str):
    return send_file(io.BytesIO(data), mimetype=XLSX, as_attachment=True, download_name=filename)


@bp.get("/sheet-format.xlsx")
@login_required
def sheet_format():
    return _xlsx(sample_format(), "parent-notifier-sheet-format.xlsx")


@bp.get("/classes/<int:class_id>/sem/<int:number>/sheet.xlsx")
@login_required
def semester_sheet(class_id: int, number: int):
    class_group, semester = load_semester(class_id, number)
    name = secure_filename(f"{class_group.name}-sem-{number}.xlsx") or f"sem-{number}.xlsx"
    return _xlsx(prefilled_sheet(class_group, semester), name)
