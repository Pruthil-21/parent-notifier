"""Uploading a semester sheet and the review page. Nothing is saved before Confirm."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from parent_notifier.core.extensions import limiter
from parent_notifier.forms.imports import ConfirmImportForm, UploadSheetForm
from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.routes.activity import log
from parent_notifier.routes.imports.review import MAX_FILENAME, owner, review
from parent_notifier.services.academics.records import classes
from parent_notifier.services.imports import staging
from parent_notifier.services.imports.apply import apply_class_list, apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from parent_notifier.services.imports.sheet_reader import SheetReadError, read_sheet

bp = Blueprint("imports", __name__, url_prefix="/classes/<int:class_id>/sem/<int:number>")


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
    if staged.sheet.is_class_list:
        outcome = apply_class_list(class_group, staged.sheet, form.update_identity.data)
        event, message = "class_list_imported", f"Class list saved: {outcome.added} students added."
    else:
        outcome = apply_import(
            class_group,
            semester,
            current_user.id,
            staged.filename,
            staged.sheet,
            update_identity=form.update_identity.data,
        )
        event = "sheet_imported"
        message = f"Sheet imported: {outcome.added} new and {outcome.updated} existing students."
    staging.discard(staged.token)
    flash(message, "success")
    log(
        "data",
        event,
        target=semester,
        class_group=class_group,
        details={"file": staged.filename, "added": outcome.added, "updated": outcome.updated},
    )
    return redirect(url_for("semesters.workspace", class_id=class_id, number=number))


@bp.post("/import/cancel")
@login_required
def cancel(class_id: int, number: int):
    class_group, semester = load_semester(class_id, number)
    form = ConfirmImportForm()
    staged = staging.load(form.token.data or "", owner(class_group, semester))
    staging.discard(form.token.data or "")
    # Backing out of a new class's first review leaves no empty class behind.
    if staged is not None and staged.sheet.new_class and classes.is_unused(class_group):
        name, removed_id = class_group.name, class_group.id
        classes.delete_class(class_group)
        log("data", "class_deleted", target=("class", removed_id, name))
        flash(f"Nothing was saved, and {name} was not created.", "info")
        return redirect(url_for("classes.index"))
    flash("Import cancelled. Nothing was saved.", "info")
    return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
