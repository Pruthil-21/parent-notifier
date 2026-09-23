"""A student's page within a semester, for browsers without the popup."""

from flask import Blueprint, abort, render_template
from flask_login import login_required

from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.services.academics import semester_view

bp = Blueprint("students", __name__, url_prefix="/classes/<int:class_id>")


@bp.get("/sem/<int:number>/students/<int:student_id>")
@login_required
def detail(class_id: int, number: int, student_id: int):
    class_group, semester = load_semester(class_id, number)
    view = semester_view.build(class_group, semester)
    row = semester_view.find_row(view, student_id)
    if row is None:
        abort(404)
    return render_template(
        "pages/academics/students/detail.html",
        class_group=class_group,
        semester=semester,
        view=view,
        row=row,
    )
