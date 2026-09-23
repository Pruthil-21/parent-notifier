"""Undoing the last import of a semester."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.services.imports import undo

bp = Blueprint("import_undo", __name__, url_prefix="/classes/<int:class_id>/sem/<int:number>")


@bp.get("/import/undo")
@login_required
def confirm_undo(class_id: int, number: int):
    """The confirmation as a page, for browsers without JavaScript."""
    class_group, semester = load_semester(class_id, number)
    batch = undo.latest_undoable(semester)
    if batch is None:
        return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
    return render_template(
        "pages/imports/undo/page.html", class_group=class_group, semester=semester, batch=batch
    )


@bp.post("/import/undo")
@login_required
def undo_last(class_id: int, number: int):
    _class_group, semester = load_semester(class_id, number)
    batch = undo.latest_undoable(semester)
    if batch is None:
        flash("There is no import to undo for this semester.", "error")
    else:
        undo.undo_import(semester, batch)
        flash(f"Import of {batch.filename} undone. Sem {number} is back as it was.", "success")
    return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
