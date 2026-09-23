"""A class's semesters: the semester page and adding a semester."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_required

from parent_notifier.forms.academics import AddSemesterForm, add_semester_form
from parent_notifier.routes.academics.classes import load_class
from parent_notifier.services.academics import semesters

bp = Blueprint("semesters", __name__, url_prefix="/classes/<int:class_id>")


@bp.get("/sem/<int:number>")
@login_required
def workspace(class_id: int, number: int):
    class_group = load_class(class_id)
    semester = semesters.get_semester(class_group, number)
    if semester is None:
        abort(404)
    return render_template(
        "pages/academics/semesters/workspace.html",
        class_group=class_group,
        semester=semester,
        summaries=semesters.summaries(class_group),
        add_form=add_semester_form(class_group),
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
