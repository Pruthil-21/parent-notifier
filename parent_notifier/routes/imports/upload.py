"""Uploading a semester sheet and the review page. Nothing is saved before Confirm."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from parent_notifier.core.extensions import limiter
from parent_notifier.forms.imports import ConfirmImportForm, UploadSheetForm
from parent_notifier.models.academics import ClassGroup, Semester
from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.routes.activity import log
from parent_notifier.services.imports import staging
from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.compare import compare
from parent_notifier.services.imports.sheet_parser import ParsedSheet, parse_sheet
from parent_notifier.services.imports.sheet_reader import SheetReadError, read_sheet

bp = Blueprint("imports", __name__, url_prefix="/classes/<int:class_id>/sem/<int:number>")

MAX_FILENAME = 120


def owner(class_group: ClassGroup, semester: Semester) -> staging.Owner:
    return staging.Owner(current_user.id, class_group.id, semester.id)


def _upload_page(class_group, semester, form):
    return render_template(
        "pages/imports/upload/page.html", class_group=class_group, semester=semester, form=form
    )


@bp.get("/upload")
@login_required
def upload_page(class_id: int, number: int):
    """The upload form as a page, for browsers without JavaScript."""
    class_group, semester = load_semester(class_id, number)
    return _upload_page(class_group, semester, UploadSheetForm.for_semester(semester))


@bp.post("/import")
@login_required
@limiter.limit("60 per hour")
def upload(class_id: int, number: int):
    class_group, semester = load_semester(class_id, number)
    form = UploadSheetForm()
    if not form.validate_on_submit():
        return _upload_page(class_group, semester, form)
    filename = (form.sheet.data.filename or "sheet")[:MAX_FILENAME]
    try:
        grid = read_sheet(filename, form.sheet.data.read())
    except SheetReadError as error:
        form.sheet.errors.append(str(error))
        return _upload_page(class_group, semester, form)
    sheet = parse_sheet(grid, class_group.midsem_max)
    sheet.attendance_from, sheet.attendance_to = form.period()
    token = None
    if not sheet.errors:
        token = staging.stage(owner(class_group, semester), filename, sheet)
    return review(class_group, semester, filename, sheet, ConfirmImportForm(token=token))


def review(class_group, semester, filename: str, sheet: ParsedSheet, form):
    return render_template(
        "pages/imports/review/page.html",
        class_group=class_group,
        semester=semester,
        filename=filename,
        sheet=sheet,
        comparison=compare(class_group, sheet),
        form=form,
    )


@bp.post("/import/confirm")
@login_required
def confirm(class_id: int, number: int):
    class_group, semester = load_semester(class_id, number)
    form = ConfirmImportForm()
    staged = None
    if form.validate_on_submit():
        staged = staging.load(form.token.data, owner(class_group, semester))
    if staged is None:
        # Expired, already confirmed in another tab, or not this semester's sheet.
        flash("This review has expired, so nothing was saved. Upload the sheet again.", "error")
        return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
    outcome = apply_import(
        class_group,
        semester,
        current_user.id,
        staged.filename,
        staged.sheet,
        update_identity=form.update_identity.data,
    )
    staging.discard(staged.token)
    flash(
        f"Sheet imported: {outcome.added} new and {outcome.updated} existing students.",
        "success",
    )
    log(
        "data",
        "sheet_imported",
        target=semester,
        class_group=class_group,
        details={"file": staged.filename, "added": outcome.added, "updated": outcome.updated},
    )
    return redirect(url_for("semesters.workspace", class_id=class_id, number=number))


@bp.post("/import/cancel")
@login_required
def cancel(class_id: int, number: int):
    load_semester(class_id, number)
    form = ConfirmImportForm()
    staging.discard(form.token.data or "")
    flash("Import cancelled. Nothing was saved.", "info")
    return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
