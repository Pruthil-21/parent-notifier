"""A class's semesters: the semester page, adding one and removing an empty one."""

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from parent_notifier.forms.academics import AddSemesterForm, add_semester_form
from parent_notifier.forms.imports import UploadSheetForm
from parent_notifier.models.academics import ClassGroup, Semester
from parent_notifier.routes.academics.classes import load_class
from parent_notifier.services.academics import grid_filters, semester_view, semesters
from parent_notifier.services.imports import undo
from parent_notifier.services.messaging import pacing, previews, send_log
from parent_notifier.services.messaging.message_templates import LANGUAGES

bp = Blueprint("semesters", __name__, url_prefix="/classes/<int:class_id>")


def load_semester(class_id: int, number: int) -> tuple[ClassGroup, Semester]:
    """The signed-in mentor's class and one of its semesters, or 404."""
    class_group = load_class(class_id)
    semester = semesters.get_semester(class_group, number)
    if semester is None:
        abort(404)
    return class_group, semester


def _popup_payload(class_group, semester, view, rows, marks, pending) -> list[dict]:
    """The popup's data for the rows on screen: figures, both messages and send status."""
    config = current_app.config
    context = previews.context_for(
        semester.number, class_group.midsem_max, current_user.full_name, config
    )
    payload = semester_view.popup_payload(rows, view.rules)
    labels = _labels(view, marks)
    for entry, row in zip(payload, rows, strict=True):
        entry["messages"] = previews.messages_for(row, context)
        entry["mark"] = labels[row.id]
        entry["pending"] = row.id in pending
    return payload


def _labels(view, marks) -> dict[int, str]:
    timezone = current_app.config["APP_TIMEZONE"]
    return {
        row.id: send_log.label(marks.get(row.id), row.phone_e164 is not None, timezone)
        for row in view.rows
    }


@bp.get("/sem/<int:number>")
@login_required
def workspace(class_id: int, number: int):
    class_group, semester = load_semester(class_id, number)
    view = semester_view.build(class_group, semester)
    query = grid_filters.GridQuery.from_args(request.args)
    marks = send_log.marks_for(semester)
    pending = send_log.pending_ids(view.rows, marks)
    rows = grid_filters.apply(view.rows, query, pending)
    return render_template(
        "pages/academics/semesters/workspace.html",
        class_group=class_group,
        semester=semester,
        summaries=semesters.summaries(class_group),
        add_form=add_semester_form(class_group),
        can_remove=semesters.is_empty(semester),
        upload_form=UploadSheetForm(formdata=None),
        last_import=undo.latest_undoable(semester),
        view=view,
        query=query,
        rows=rows,
        status_filters=grid_filters.STATUS_FILTERS,
        popup=_popup_payload(class_group, semester, view, rows, marks, pending),
        pending_count=len(pending),
        pacing=pacing.status_for(current_user, current_app.config["APP_TIMEZONE"]),
        marks=marks,
        labels=_labels(view, marks),
        sent_ids={sid for sid, mark in marks.items() if mark.status == "sent"},
        languages=LANGUAGES,
    )


@bp.get("/semesters/new")
@login_required
def new_semester(class_id: int):
    """The add-semester form as a page, for browsers without JavaScript."""
    class_group = load_class(class_id)
    return render_template(
        "pages/academics/semesters/new.html",
        class_group=class_group,
        form=add_semester_form(class_group),
    )


@bp.post("/semesters")
@login_required
def add_semester(class_id: int):
    class_group = load_class(class_id)
    form = AddSemesterForm()
    if not form.validate_on_submit():
        return render_template(
            "pages/academics/semesters/new.html", class_group=class_group, form=form
        )
    semester, created = semesters.add_semester(class_group, form.number.data)
    if created:
        flash(f"Sem {semester.number} added.", "success")
    else:
        flash(f"Sem {semester.number} already exists, so it is open now.", "info")
    return redirect(url_for("semesters.workspace", class_id=class_id, number=semester.number))


@bp.get("/sem/<int:number>/remove")
@login_required
def confirm_remove(class_id: int, number: int):
    """The confirmation as a page, for browsers without JavaScript."""
    class_group, semester = load_semester(class_id, number)
    return render_template(
        "pages/academics/semesters/remove.html", class_group=class_group, semester=semester
    )


@bp.post("/sem/<int:number>/remove")
@login_required
def remove(class_id: int, number: int):
    _class_group, semester = load_semester(class_id, number)
    if semesters.remove_if_empty(semester):
        flash(f"Sem {number} removed.", "success")
        return redirect(url_for("classes.open_class", class_id=class_id))
    flash(f"Sem {number} has a sheet, so it cannot be removed.", "error")
    return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
