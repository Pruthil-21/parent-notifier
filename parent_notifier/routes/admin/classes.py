"""The admin's list of every class, and the read-only view of any mentor's class.

These pages only read. Every page that changes a class keeps checking that the signed-in
mentor owns it, so the admin cannot send from, edit or import into another mentor's
class even by hand-made requests.
"""

from flask import Blueprint, abort, redirect, render_template, request, url_for

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.models.accounts import Mentor
from parent_notifier.routes.academics.semesters import workspace_context
from parent_notifier.routes.admin.access import admin_required
from parent_notifier.services.academics.records import semesters
from parent_notifier.services.academics.views import semester_view
from parent_notifier.services.admin import overview
from parent_notifier.services.shared import departments

bp = Blueprint("admin_classes", __name__, url_prefix="/admin/classes")

VIEW = {
    "read_only": True,
    "workspace_endpoint": "admin_classes.workspace",
    "student_endpoint": "admin_classes.student",
}


def _load(class_id: int, number: int | None = None):
    class_group = db.session.get(ClassGroup, class_id)
    if class_group is None:
        abort(404)
    semester = None
    if number is not None:
        semester = semesters.get_semester(class_group, number)
        if semester is None:
            abort(404)
    return class_group, semester, db.session.get(Mentor, class_group.mentor_id)


@bp.get("/")
@admin_required
def index():
    filters = overview.ClassFilters.from_args(request.args)
    return render_template(
        "pages/admin/classes/index.html",
        filters=filters,
        page=overview.class_page(filters),
        department_list=departments.names(),
        years=overview.batch_years(),
        sorts=overview.SORTS,
    )


@bp.get("/<int:class_id>")
@admin_required
def open_class(class_id: int):
    class_group, _, owner = _load(class_id)
    if class_group.semesters:
        latest = class_group.semesters[-1].number
        return redirect(url_for("admin_classes.workspace", class_id=class_id, number=latest))
    return redirect(url_for("admin_users.detail", account_id=owner.id))


@bp.get("/<int:class_id>/sem/<int:number>")
@admin_required
def workspace(class_id: int, number: int):
    class_group, semester, owner = _load(class_id, number)
    return render_template(
        "pages/academics/semesters/workspace.html",
        **workspace_context(class_group, semester, owner),
        owner=owner,
        **VIEW,
    )


@bp.get("/<int:class_id>/sem/<int:number>/students/<int:student_id>")
@admin_required
def student(class_id: int, number: int, student_id: int):
    class_group, semester, owner = _load(class_id, number)
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
        owner=owner,
        **VIEW,
    )
