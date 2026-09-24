"""Signing in and out, and resetting a forgotten password with a recovery code."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user

from parent_notifier.forms.accounts import ChooseOwnPasswordForm, ResetPasswordForm, SignInForm
from parent_notifier.routes.accounts import throttling
from parent_notifier.routes.accounts.sessions import safe_next, show_recovery_code, start_session
from parent_notifier.services.accounts import credentials, registration

bp = Blueprint("auth", __name__)

INCORRECT_SIGN_IN = "Username or password is incorrect."
WAITING_FOR_APPROVAL = (
    "Your account is waiting for the admin's approval. Try again once it is approved."
)
INCORRECT_RESET = "Username or recovery code is incorrect."
SIGN_IN_TEMPLATE = "pages/accounts/sign_in.html"
RESET_TEMPLATE = "pages/accounts/reset_password.html"


@bp.route("/sign-in", methods=["GET", "POST"])
@throttling.throttle_failed_attempts
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))
    form = SignInForm(next=request.args.get("next", ""))
    if form.validate_on_submit():
        mentor = credentials.authenticate(form.username.data, form.password.data)
        if mentor and not mentor.approved:
            # Said only after the right password, so it reveals nothing to a guesser.
            form.form_errors.append(WAITING_FOR_APPROVAL)
        elif mentor:
            start_session(mentor, remember=form.remember.data)
            code = registration.record_sign_in(mentor)
            if mentor.must_change_password:
                return redirect(url_for("auth.choose_password"))
            if code:
                return show_recovery_code(code, then="home")
            return redirect(safe_next(form.next.data))
        else:
            throttling.record_failed_attempt()
            form.form_errors.append(INCORRECT_SIGN_IN)
    return _sign_in_page(form)


def _sign_in_page(form, status: int = 200):
    signup = registration.signup_mode()
    return render_template(SIGN_IN_TEMPLATE, form=form, signup=signup), status


@bp.route("/reset-password", methods=["GET", "POST"])
@throttling.throttle_failed_attempts
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        result = registration.reset_password(
            form.username.data, form.recovery_code.data, form.new_password.data
        )
        if result:
            mentor, new_code = result
            start_session(mentor)
            flash(
                "Your password has been reset. Your old recovery code no longer works.", "success"
            )
            return show_recovery_code(new_code, then="home")
        throttling.record_failed_attempt()
        form.form_errors.append(INCORRECT_RESET)
    return render_template(RESET_TEMPLATE, form=form)


@bp.errorhandler(429)
def too_many_attempts(_error):
    """A lockout keeps the mentor on the form, with the wait in the error summary."""
    if request.endpoint == "auth.reset_password":
        form = ResetPasswordForm()
        form.form_errors.append(throttling.lockout_message("password reset"))
        return render_template(RESET_TEMPLATE, form=form), 429
    form = SignInForm()
    form.form_errors.append(throttling.lockout_message("sign-in"))
    return _sign_in_page(form, 429)


@bp.post("/sign-out")
def sign_out():
    # Clear first: logout_user() leaves a note in the session that deletes the
    # remember-me cookie, and clearing afterwards would throw that note away.
    session.clear()
    logout_user()
    flash("You have signed out.", "success")
    return redirect(url_for("auth.sign_in"))


# Pages a mentor with an admin-set password can still reach before choosing their own.
_BEFORE_OWN_PASSWORD = {"auth.choose_password", "auth.sign_out", "static", "speculation_rules"}


@bp.before_app_request
def require_own_password():
    """An admin-set password opens only the page for choosing a new one."""
    if (
        current_user.is_authenticated
        and current_user.must_change_password
        and request.endpoint not in _BEFORE_OWN_PASSWORD
    ):
        return redirect(url_for("auth.choose_password"))
    return None


@bp.route("/choose-password", methods=["GET", "POST"])
@login_required
def choose_password():
    if not current_user.must_change_password:
        return redirect(url_for("home.index"))
    form = ChooseOwnPasswordForm()
    if form.validate_on_submit():
        mentor = current_user._get_current_object()
        code = registration.choose_own_password(mentor, form.new_password.data)
        start_session(mentor)  # set_password signed out every session, this one too
        flash("Your password is set.", "success")
        return show_recovery_code(code, then="home")
    return render_template("pages/accounts/choose_password.html", form=form)
