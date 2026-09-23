"""A class's semesters: the semester page, adding one and removing an empty one."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_required

from parent_notifier.forms.academics import AddSemesterForm, add_semester_form
from parent_notifier.forms.imports import UploadSheetForm
from parent_notifier.models.academics import ClassGroup, Semester
from parent_notifier.routes.academics.classes import load_class
from parent_notifier.services.academics import semester_view, semesters
from parent_notifier.services.imports import undo

bp = Blueprint("semesters", __name__, url_prefix="/classes/<int:class_id>")


def load_semester(class_id: int, number: int) -> tuple[ClassGroup, Semester]:
    """The signed-in mentor's class and one of its semesters, or 404."""
    class_group = load_class(class_id)
    semester = semesters.get_semester(class_group, number)
    if semester is None:
        abort(404)
    return class_group, semester


@bp.get("/sem/<int:number>")
@login_required
def workspace(class_id: int, number: int):
    class_group, semester = load_semester(class_id, number)
    return render_template(
        "pages/academics/semesters/workspace.html",
        class_group=class_group,
        semester=semester,
        summaries=semesters.summaries(class_group),
        add_form=add_semester_form(class_group),
        can_remove=semesters.is_empty(semester),
        upload_form=UploadSheetForm(formdata=None),
        last_import=undo.latest_undoable(semester),
        view=semester_view.build(class_group, semester),
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
