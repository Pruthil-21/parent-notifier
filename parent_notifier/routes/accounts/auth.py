"""Signing in and out."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, logout_user

from parent_notifier.forms.accounts import SignInForm
from parent_notifier.routes.accounts import throttling
from parent_notifier.routes.accounts.sessions import safe_next, start_session
from parent_notifier.services.accounts import credentials

bp = Blueprint("auth", __name__)

INCORRECT_SIGN_IN = "Username or password is incorrect."


@bp.route("/sign-in", methods=["GET", "POST"])
@throttling.throttle_failed_attempts
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))
    form = SignInForm(next=request.args.get("next", ""))
    if form.validate_on_submit():
        mentor = credentials.authenticate(form.username.data, form.password.data)
        if mentor:
            start_session(mentor, remember=form.remember.data)
            return redirect(safe_next(form.next.data))
        throttling.record_failed_attempt()
        form.form_errors.append(INCORRECT_SIGN_IN)
    return render_template("pages/accounts/sign_in.html", form=form)


@bp.errorhandler(429)
def too_many_attempts(_error):
    """A lockout keeps the mentor on the form, with the wait in the error summary."""
    form = SignInForm()
    form.form_errors.append(throttling.lockout_message("sign-in"))
    return render_template("pages/accounts/sign_in.html", form=form), 429


@bp.post("/sign-out")
def sign_out():
    # Clear first: logout_user() leaves a note in the session that deletes the
    # remember-me cookie, and clearing afterwards would throw that note away.
    session.clear()
    logout_user()
    flash("You have signed out.", "success")
    return redirect(url_for("auth.sign_in"))
