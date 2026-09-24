"""College-wide settings the admin keeps: who may create an account, the
departments, and the announcement banner."""

from flask import Blueprint, flash, redirect, render_template, url_for

from parent_notifier.forms.admin import SignupModeForm
from parent_notifier.routes.activity import log
from parent_notifier.routes.admin.access import admin_required, confirmed_password_required
from parent_notifier.services.accounts import registration

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
