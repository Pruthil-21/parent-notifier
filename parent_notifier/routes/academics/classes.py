"""The classes list, creating a class, and opening one."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from parent_notifier.core.navigation import register_child_links
from parent_notifier.forms.academics import CLASS_NAME_TAKEN, ClassDetailsForm, add_semester_form
from parent_notifier.models.academics import ClassGroup
from parent_notifier.services.academics.records import classes, ownership

bp = Blueprint("classes", __name__, url_prefix="/classes")


def load_class(class_id: int) -> ClassGroup:
    """The signed-in mentor's class, or 404 for anyone else's id."""
    class_group = ownership.get_class(current_user.id, class_id)
    if class_group is None:
        abort(404)
    return class_group


def _class_links() -> list[dict[str, object]]:
    if not current_user.is_authenticated:
        return []
    current_id = (request.view_args or {}).get("class_id")
    return [
        {
            "label": name,
            "url": url_for("classes.open_class", class_id=class_id),
            "active": class_id == current_id,
        }
        for class_id, name in ownership.class_links(current_user.id)
    ]


bp.record_once(lambda state: register_child_links(state.app, "classes.index", _class_links))


@bp.get("/")
@login_required
def index():
    rows = ownership.list_classes(current_user.id)
    return render_template("pages/academics/classes/index.html", rows=rows)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_class():
    form = ClassDetailsForm(mentor_id=current_user.id)
    if form.validate_on_submit():
        try:
            class_group = classes.create_class(
                current_user.id, form.name.data, form.department.data, form.admission_year.data
            )
        except classes.ClassNameTakenError:
            form.name.errors.append(CLASS_NAME_TAKEN)
        else:
            flash(f"Class {class_group.name} created.", "success")
            return redirect(url_for("classes.open_class", class_id=class_group.id))
    return render_template("pages/academics/classes/new.html", form=form)


@bp.get("/<int:class_id>")
@login_required
def open_class(class_id: int):
    """Open the latest semester, or the start panel when there is none yet."""
    class_group = load_class(class_id)
    if class_group.semesters:
        latest = class_group.semesters[-1].number
        return redirect(url_for("semesters.workspace", class_id=class_id, number=latest))
    return render_template(
        "pages/academics/classes/start.html",
        class_group=class_group,
        add_form=add_semester_form(class_group),
    )
