"""Signing in and out."""

from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from parent_notifier.forms.accounts import SignInForm
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import credentials

bp = Blueprint("auth", __name__)

INCORRECT_SIGN_IN = "Username or password is incorrect."


@bp.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))
    form = SignInForm(next=request.args.get("next", ""))
    if form.validate_on_submit():
        mentor = credentials.authenticate(form.username.data, form.password.data)
        if mentor:
            start_session(mentor, remember=form.remember.data)
            return redirect(safe_next(form.next.data))
        form.form_errors.append(INCORRECT_SIGN_IN)
    return render_template("pages/accounts/sign_in.html", form=form)


@bp.post("/sign-out")
def sign_out():
    # Clear first: logout_user() leaves a note in the session that deletes the
    # remember-me cookie, and clearing afterwards would throw that note away.
    session.clear()
    logout_user()
    flash("You have signed out.", "success")
    return redirect(url_for("auth.sign_in"))


def start_session(mentor: Mentor, remember: bool = False) -> None:
    """Nothing from before sign-in carries over into the signed-in session."""
    session.clear()
    login_user(mentor, remember=remember)


def safe_next(target: str | None) -> str:
    """Follow `next` only to a path on this site. Scheme-relative URLs, backslashes and
    control characters (browsers drop tabs, so "/<tab>/x" becomes "//x") all go home."""
    if (
        target
        and target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
        and all(ord(char) >= 32 for char in target)
    ):
        parts = urlsplit(target)
        if not parts.scheme and not parts.netloc:
            return target
    return url_for("home.index")
