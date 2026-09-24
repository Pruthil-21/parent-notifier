"""College-wide settings the admin keeps: who may create an account, the
departments, and the announcement banner."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for

from parent_notifier.forms.admin import DepartmentForm, SignupModeForm
from parent_notifier.routes.activity import log
from parent_notifier.routes.admin.access import admin_required, confirmed_password_required
from parent_notifier.services.accounts import registration
from parent_notifier.services.shared import departments

bp = Blueprint("admin_settings", __name__, url_prefix="/admin/settings")


def _settings_page(form=None, status: int = 200):
    form = form or SignupModeForm(formdata=None, mode=registration.signup_mode())
    return render_template("pages/admin/settings/index.html", form=form), status


@bp.get("/")
@admin_required
def index():
    return _settings_page()


@bp.post("/")
@confirmed_password_required
def save():
    form = SignupModeForm()
    if not form.validate_on_submit():
        return _settings_page(form, 400)
    registration.set_signup_mode(form.mode.data)
    log("admin", "signup_mode_changed", details={"mode": form.mode.data})
    flash("Settings saved.", "success")
    return redirect(url_for("admin_settings.index"))


def _departments_page(add_form=None, errors=None, status: int = 200):
    """`errors` holds a rename or removal problem for one department, by its id."""
    return render_template(
        "pages/admin/settings/departments.html",
        rows=departments.listing(),
        add_form=add_form or DepartmentForm(formdata=None),
        errors=errors or {},
    ), status


def _department(department_id: int):
    department = departments.get(department_id)
    if department is None:
        abort(404)
    return department


@bp.get("/departments")
@admin_required
def departments_page():
    return _departments_page()


@bp.post("/departments")
@admin_required
def add_department():
    form = DepartmentForm()
    if not form.validate_on_submit():
        return _departments_page(add_form=form, status=400)
    department = departments.add(form.name.data)
    log("admin", "department_added", target=("department", department.id, department.name))
    flash(f"{department.name} added.", "success")
    return redirect(url_for("admin_settings.departments_page"))


@bp.post("/departments/<int:department_id>/rename")
@confirmed_password_required
def rename_department(department_id: int):
    department = _department(department_id)
    old_name = department.name
    form = DepartmentForm(current=old_name)
    if not form.validate_on_submit():
        message = next(iter(form.errors.values()))[0]
        return _departments_page(errors={department.id: message}, status=400)
    if form.name.data != old_name:
        departments.rename(department, form.name.data)
        log(
            "admin",
            "department_renamed",
            target=("department", department.id, form.name.data),
            details={"was": old_name},
        )
        flash(f"{old_name} is now {form.name.data}, for every mentor and class.", "success")
    return redirect(url_for("admin_settings.departments_page"))


@bp.post("/departments/<int:department_id>/remove")
@confirmed_password_required
def remove_department(department_id: int):
    department = _department(department_id)
    name = department.name
    try:
        departments.remove(department)
    except departments.DepartmentInUseError:
        mentors, classes = departments.usage(name)
        return _departments_page(
            errors={department.id: f"Still used by {mentors} mentors and {classes} classes"},
            status=400,
        )
    log("admin", "department_removed", target=("department", department_id, name))
    flash(f"{name} removed.", "success")
    return redirect(url_for("admin_settings.departments_page"))
