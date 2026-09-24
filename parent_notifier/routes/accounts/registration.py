"""Creating an account, and the page that shows a new recovery code once."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from parent_notifier.core.extensions import limiter
from parent_notifier.forms.accounts import USERNAME_TAKEN, CreateAccountForm, RecoveryCodeSavedForm
from parent_notifier.routes.accounts import sessions, throttling
from parent_notifier.services.accounts import recovery_codes, registration

bp = Blueprint("registration", __name__)

CREATE_TEMPLATE = "pages/accounts/create_account.html"


@bp.route("/create-account", methods=["GET", "POST"])
# Counts accounts actually created, which caps sign-up spam from one computer.
@limiter.limit("10 per hour", methods=["POST"], deduct_when=lambda r: r.status_code == 302)
def create_account():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))
    form = CreateAccountForm()
    if form.validate_on_submit():
        try:
            mentor, code = registration.create_mentor(
                form.full_name.data,
                form.username.data,
                form.whatsapp_number.data,
                form.password.data,
                form.department.data,
            )
        except registration.UsernameTakenError:
            form.username.errors.append(USERNAME_TAKEN)
        else:
            sessions.start_session(mentor)
            flash("Your account is ready.", "success")
            return sessions.show_recovery_code(code, then="home")
    return render_template(CREATE_TEMPLATE, form=form)


@bp.errorhandler(429)
def too_many_accounts(_error):
    form = CreateAccountForm()
    form.form_errors.append(
        f"Too many accounts were created from this computer. "
        f"Try again in {throttling.retry_wait()}."
    )
    return render_template(CREATE_TEMPLATE, form=form), 429


@bp.route("/recovery-code", methods=["GET", "POST"])
@login_required
def recovery_code():
    code = sessions.pending_recovery_code()
    if code is None:
        return redirect(url_for("home.index"))
    form = RecoveryCodeSavedForm()
    if form.validate_on_submit():
        return redirect(sessions.finish_recovery_code())
    return render_template(
        "pages/accounts/recovery_code.html",
        form=form,
        code=recovery_codes.format_for_display(code),
    )


@bp.get("/recovery-code.txt")
@login_required
def download_recovery_code():
    code = sessions.pending_recovery_code()
    if code is None:
        abort(404)
    text = (
        f"Parent Notifier recovery code for {current_user.username}\n\n"
        f"{recovery_codes.format_for_display(code)}\n\n"
        "Use it on the Reset password page if you forget your password. It works once.\n"
    )
    return text, {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": 'attachment; filename="parent-notifier-recovery-code.txt"',
    }
