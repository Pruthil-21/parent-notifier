"""Class settings: details, status rules, finishing the batch and deleting the class.
Each section saves on its own."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from parent_notifier.forms.academics import (
    CLASS_NAME_TAKEN,
    ClassDetailsForm,
    DeleteClassForm,
    StatusRulesForm,
)
from parent_notifier.models.academics import ClassGroup
from parent_notifier.routes.academics.classes import load_class
from parent_notifier.routes.activity import log
from parent_notifier.services.academics.records import classes

bp = Blueprint("class_settings", __name__, url_prefix="/classes/<int:class_id>/settings")


def _details_form(class_group: ClassGroup, formdata=None) -> ClassDetailsForm:
    return ClassDetailsForm(
        formdata=formdata, obj=class_group, mentor_id=current_user.id, class_id=class_group.id
    )


def _render(class_group: ClassGroup, details_form=None, rules_form=None, delete_form=None):
    return render_template(
        "pages/academics/classes/settings/index.html",
        class_group=class_group,
        details_form=details_form or _details_form(class_group),
        rules_form=rules_form or StatusRulesForm(formdata=None, obj=class_group),
        delete_form=delete_form or DeleteClassForm(formdata=None, class_name=class_group.name),
    )


@bp.get("/")
@login_required
def index(class_id: int):
    return _render(load_class(class_id))


@bp.post("/details")
@login_required
def save_details(class_id: int):
    class_group = load_class(class_id)
    form = ClassDetailsForm(mentor_id=current_user.id, class_id=class_group.id)
    if form.validate_on_submit():
        try:
            classes.update_details(
                class_group, form.name.data, form.department.data, form.admission_year.data
            )
        except classes.ClassNameTakenError:
            form.name.errors.append(CLASS_NAME_TAKEN)
        else:
            flash("Class details saved.", "success")
            log("data", "class_edited", target=class_group, class_group=class_group)
            return redirect(url_for("class_settings.index", class_id=class_id))
    return _render(class_group, details_form=form)


@bp.post("/rules")
@login_required
def save_rules(class_id: int):
    class_group = load_class(class_id)
    form = StatusRulesForm()
    if form.validate_on_submit():
        classes.update_rules(
            class_group,
            form.attendance_threshold.data,
            form.midsem_pass_mark.data,
            form.midsem_max.data,
        )
        flash("Status rules saved.", "success")
        log(
            "data",
            "class_rules_changed",
            target=class_group,
            class_group=class_group,
            details={
                "attendance": form.attendance_threshold.data,
                "pass_mark": form.midsem_pass_mark.data,
                "midsem_max": form.midsem_max.data,
            },
        )
        return redirect(url_for("class_settings.index", class_id=class_id))
    return _render(class_group, rules_form=form)


@bp.post("/finish")
@login_required
def finish(class_id: int):
    class_group = load_class(class_id)
    if class_group.finished_at is None:
        classes.finish(class_group)
        log("data", "class_finished", target=class_group, class_group=class_group)
        flash(f"{class_group.name} moved to Past batches. You can still send messages.", "success")
    return redirect(url_for("class_settings.index", class_id=class_id))


@bp.post("/reopen")
@login_required
def reopen(class_id: int):
    class_group = load_class(class_id)
    if class_group.finished_at is not None:
        classes.reopen(class_group)
        log("data", "class_reopened", target=class_group, class_group=class_group)
        flash(f"{class_group.name} is a current class again.", "success")
    return redirect(url_for("class_settings.index", class_id=class_id))


@bp.post("/delete")
@login_required
def delete(class_id: int):
    class_group = load_class(class_id)
    form = DeleteClassForm(class_name=class_group.name)
    if form.validate_on_submit():
        name = class_group.name
        classes.delete_class(class_group)
        log("data", "class_deleted", target=("class", class_id, name))
        flash(f"Class {name} deleted, with its semesters and students.", "success")
        return redirect(url_for("classes.index"))
    return _render(class_group, delete_form=form)
