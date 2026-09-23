"""Creating an account."""

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

from parent_notifier.core.extensions import limiter
from parent_notifier.forms.accounts import USERNAME_TAKEN, CreateAccountForm
from parent_notifier.routes.accounts import throttling
from parent_notifier.routes.accounts.auth import start_session
from parent_notifier.services.accounts import registration

bp = Blueprint("registration", __name__)

TEMPLATE = "pages/accounts/create_account.html"


@bp.route("/create-account", methods=["GET", "POST"])
# Counts accounts actually created, which caps sign-up spam from one computer.
@limiter.limit("10 per hour", methods=["POST"], deduct_when=lambda r: r.status_code == 302)
def create_account():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))
    form = CreateAccountForm()
    if form.validate_on_submit():
        try:
            mentor, _code = registration.create_mentor(
                form.full_name.data,
                form.username.data,
                form.whatsapp_number.data,
                form.password.data,
            )
        except registration.UsernameTakenError:
            form.username.errors.append(USERNAME_TAKEN)
        else:
            start_session(mentor)
            return redirect(url_for("home.index"))
    return render_template(TEMPLATE, form=form)


@bp.errorhandler(429)
def too_many_accounts(_error):
    form = CreateAccountForm()
    form.form_errors.append(
        f"Too many accounts were created from this computer. "
        f"Try again in {throttling.retry_wait()}."
    )
    return render_template(TEMPLATE, form=form), 429
