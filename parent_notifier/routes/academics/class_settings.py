"""Class settings: details and status rules. Each section saves on its own."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from parent_notifier.forms.academics import CLASS_NAME_TAKEN, ClassDetailsForm, StatusRulesForm
from parent_notifier.models.academics import ClassGroup
from parent_notifier.routes.academics.classes import load_class
from parent_notifier.services.academics import classes

bp = Blueprint("class_settings", __name__, url_prefix="/classes/<int:class_id>/settings")


def _details_form(class_group: ClassGroup, formdata=None) -> ClassDetailsForm:
    return ClassDetailsForm(
        formdata=formdata, obj=class_group, mentor_id=current_user.id, class_id=class_group.id
    )


def _render(class_group: ClassGroup, details_form=None, rules_form=None):
    return render_template(
        "pages/academics/classes/settings/index.html",
        class_group=class_group,
        details_form=details_form or _details_form(class_group),
        rules_form=rules_form or StatusRulesForm(formdata=None, obj=class_group),
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
        return redirect(url_for("class_settings.index", class_id=class_id))
    return _render(class_group, rules_form=form)
