"""The classes list, creating a class, and opening one."""

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from parent_notifier.core.navigation import register_child_links
from parent_notifier.forms.academics import CLASS_NAME_TAKEN, NewClassForm, add_semester_form
from parent_notifier.forms.imports import ConfirmImportForm
from parent_notifier.models.academics import DEFAULT_MIDSEM_MAX, ClassGroup
from parent_notifier.routes.academics.class_menu import MenuClass, class_menu
from parent_notifier.routes.activity import log
from parent_notifier.routes.imports.review import MAX_FILENAME, owner, review
from parent_notifier.services.academics.records import classes, ownership, semesters
from parent_notifier.services.imports import staging
from parent_notifier.services.imports.sheet_parser import parse_sheet
from parent_notifier.services.imports.sheet_reader import SheetReadError, read_sheet

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
    rows = ownership.class_links(current_user.id)
    return class_menu(
        [
            MenuClass(r.id, r.name, r.department, r.admission_year, r.finished_at is not None)
            for r in rows
        ],
        lambda class_id: url_for("classes.open_class", class_id=class_id),
        (request.view_args or {}).get("class_id"),
        own_department=current_user.department,
    )


bp.record_once(lambda state: register_child_links(state.app, "classes.index", _class_links))


@bp.get("/")
@login_required
def index():
    rows = ownership.list_classes(current_user.id)
    return render_template("pages/academics/classes/index.html", rows=rows)


def _read_new_class_file(form: NewClassForm):
    """The file's name and parsed rows, or None with its problems added to the form. The
    file is checked before anything is created, so a bad file leaves nothing behind."""
    filename = (form.sheet.data.filename or "sheet")[:MAX_FILENAME]
    try:
        grid = read_sheet(filename, form.sheet.data.read())
    except SheetReadError as error:
        form.sheet.errors.append(str(error))
        return None, []
    sheet = parse_sheet(grid, DEFAULT_MIDSEM_MAX, class_list=True)
    if sheet.errors:
        form.sheet.errors.append(
            "The file has problems, listed below. Fix them and upload it again"
        )
        return None, sheet.errors
    return (filename, sheet), []


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_class():
    """Create the class and its current semester, then review the uploaded students.
    Nothing is added to the class until the review is confirmed."""
    form = NewClassForm(mentor_id=current_user.id)
    problems = []
    if form.validate_on_submit():
        read, problems = _read_new_class_file(form)
        if read is not None:
            filename, sheet = read
            try:
                class_group = classes.create_class(
                    current_user.id, form.name.data, form.department.data, form.admission_year.data
                )
            except classes.ClassNameTakenError:
                form.name.errors.append(CLASS_NAME_TAKEN)
            else:
                semester, _ = semesters.add_semester(class_group, form.semester_number())
                sheet.new_class = True
                token = staging.stage(owner(class_group, semester), filename, sheet)
                log("data", "class_created", target=class_group, class_group=class_group)
                return review(
                    class_group, semester, filename, sheet, ConfirmImportForm(token=token)
                )
    return render_template("pages/academics/classes/new.html", form=form, problems=problems)


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
