"""The profile page. Every section edits the signed-in mentor only; no ids in URLs."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from parent_notifier.forms.accounts import USERNAME_TAKEN, AccountDetailsForm, ChangePasswordForm
from parent_notifier.routes.accounts import throttling
from parent_notifier.routes.accounts.sessions import start_session
from parent_notifier.services.accounts import profile, registration
from parent_notifier.services.shared.phone import format_for_display

bp = Blueprint("profile", __name__, url_prefix="/profile")

INCORRECT_CURRENT = "Your current password is incorrect"


def _render(account_form=None, password_form=None, status: int = 200):
    """Render every section; the one that was submitted brings its errors."""
    if account_form is None:
        account_form = AccountDetailsForm(
            formdata=None,
            mentor_id=current_user.id,
            data={
                "full_name": current_user.full_name,
                "username": current_user.username,
                "whatsapp_number": format_for_display(current_user.whatsapp_number),
            },
        )
    page = render_template(
        "pages/accounts/profile/index.html",
        account_form=account_form,
        password_form=password_form or ChangePasswordForm(formdata=None),
    )
    return page, status


@bp.get("/")
@login_required
def index():
    return _render()


@bp.post("/account")
@login_required
def save_account():
    form = AccountDetailsForm(mentor_id=current_user.id)
    if form.validate_on_submit():
        try:
            profile.update_details(
                current_user, form.full_name.data, form.username.data, form.whatsapp_number.data
            )
        except registration.UsernameTakenError:
            form.username.errors.append(USERNAME_TAKEN)
        else:
            flash("Account details saved.", "success")
            return redirect(url_for("profile.index"))
    return _render(account_form=form)


@bp.post("/password")
@login_required
@throttling.throttle_failed_password_checks
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if profile.change_password(
            current_user, form.current_password.data, form.new_password.data
        ):
            # This browser stays signed in, keeping "Stay signed in" if it was chosen.
            mentor = current_user._get_current_object()
            start_session(mentor, remember="remember_token" in request.cookies)
            flash("Password changed. Other browsers have been signed out.", "success")
            return redirect(url_for("profile.index"))
        throttling.record_failed_attempt()
        form.current_password.errors.append(INCORRECT_CURRENT)
    return _render(password_form=form)


@bp.errorhandler(429)
def too_many_password_attempts(_error):
    form = ChangePasswordForm(formdata=None)
    form.form_errors.append(throttling.lockout_message("password"))
    return _render(password_form=form, status=429)
