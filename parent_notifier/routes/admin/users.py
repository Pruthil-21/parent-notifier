"""The admin's accounts list, each account's page and the actions on it."""

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from parent_notifier.core.navigation import register_child_links
from parent_notifier.forms.accounts import USERNAME_TAKEN, AccountDetailsForm
from parent_notifier.forms.admin import ConfirmPasswordForm, NewAccountForm
from parent_notifier.routes.accounts import throttling
from parent_notifier.routes.accounts.sessions import safe_next
from parent_notifier.routes.activity import log
from parent_notifier.routes.admin.access import (
    admin_required,
    confirmed_password_required,
    password_recently_confirmed,
    remember_confirmation,
)
from parent_notifier.services.accounts import credentials, profile, registration
from parent_notifier.services.admin import users
from parent_notifier.services.shared import activity, departments

bp = Blueprint("admin_users", __name__, url_prefix="/admin/users")

# The admin section's pages, in the order the navigation lists them.
ADMIN_PAGES = (
    ("Users", "admin_users.index", "admin_users"),
    ("Activity log", "admin_logs.index", "admin_logs"),
    ("Departments", "admin_settings.departments", "admin_settings.departments"),
    ("Announcement", "admin_settings.announcement", "admin_settings.announcement"),
    ("Settings", "admin_settings.index", "admin_settings.index"),
)


def _admin_links() -> list[dict[str, object]]:
    links = []
    for label, endpoint, covers in ADMIN_PAGES:
        if endpoint not in current_app.view_functions:
            continue
        active = request.endpoint == covers or request.blueprint == covers
        links.append({"label": label, "url": url_for(endpoint), "active": active})
    return links


bp.record_once(lambda state: register_child_links(state.app, "admin_users.index", _admin_links))


def load_account(account_id: int):
    account = users.get_account(account_id)
    if account is None:
        abort(404)
    return account


@bp.get("/")
@admin_required
def index():
    filters = users.Filters.from_args(request.args)
    return render_template(
        "pages/admin/users/index.html",
        filters=filters,
        page=users.account_page(filters),
        department_list=departments.names(),
    )


@bp.get("/<int:account_id>")
@admin_required
def detail(account_id: int):
    account = load_account(account_id)
    return render_template(
        "pages/admin/users/detail.html",
        account=account,
        classes=users.classes_of(account),
        recent=users.recent_activity(account),
        event_label=activity.event_label,
    )


def _other_account(account_id: int):
    """An account the admin may act on: any but their own, which Profile covers."""
    account = load_account(account_id)
    if account.id == current_user.id:
        abort(404)
    return account


def _password_ready(account, created: bool, password: str):
    """Shown once; the page is not cached and the password is not kept anywhere."""
    return render_template(
        "pages/admin/users/password_ready.html",
        account=account,
        created=created,
        password=password,
    )


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def new():
    form = NewAccountForm()
    if form.validate_on_submit():
        if not password_recently_confirmed():
            flash("Confirm your password, then create the account again.", "info")
            return redirect(
                url_for("admin_users.confirm_password", next=url_for("admin_users.new"))
            )
        try:
            account, _code = registration.create_mentor(
                form.full_name.data,
                form.username.data,
                form.whatsapp_number.data,
                registration.unguessable_password(),
                form.department.data,
            )
        except registration.UsernameTakenError:
            form.username.errors.append(USERNAME_TAKEN)
        else:
            password = registration.set_temporary_password(account)
            log("admin", "account_created", target=account)
            return _password_ready(account, True, password)
    return render_template("pages/admin/users/new.html", form=form)


@bp.route("/<int:account_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(account_id: int):
    account = _other_account(account_id)
    form = AccountDetailsForm(
        mentor_id=account.id,
        data={
            "full_name": account.full_name,
            "username": account.username,
            "whatsapp_number": account.whatsapp_number,
            "department": account.department,
        },
    )
    if form.validate_on_submit():
        try:
            profile.update_details(
                account,
                form.full_name.data,
                form.username.data,
                form.whatsapp_number.data,
                form.department.data,
            )
        except registration.UsernameTakenError:
            form.username.errors.append(USERNAME_TAKEN)
        else:
            log("admin", "account_edited", target=account)
            flash(f"{account.full_name}'s details saved.", "success")
            return redirect(url_for("admin_users.detail", account_id=account.id))
    return render_template("pages/admin/users/edit.html", form=form, account=account)


@bp.post("/<int:account_id>/reset-password")
@confirmed_password_required
def reset_password(account_id: int):
    account = _other_account(account_id)
    password = registration.set_temporary_password(account)
    log("admin", "password_reset", target=account)
    return _password_ready(account, False, password)


@bp.post("/<int:account_id>/sign-out")
@confirmed_password_required
def sign_out_everywhere(account_id: int):
    account = _other_account(account_id)
    registration.sign_out_everywhere(account)
    log("admin", "signed_out_everywhere", target=account)
    flash(f"{account.full_name} is signed out on every computer and phone.", "success")
    return redirect(url_for("admin_users.detail", account_id=account.id))


@bp.route("/confirm-password", methods=["GET", "POST"])
@admin_required
@throttling.throttle_failed_password_checks
def confirm_password():
    form = ConfirmPasswordForm()
    back = safe_next(request.args.get("next"))
    if form.validate_on_submit():
        if credentials.authenticate(current_user.username, form.password.data) == current_user:
            remember_confirmation()
            return redirect(back)
        throttling.record_failed_attempt()
        log(
            "security",
            "sign_in_failed",
            succeeded=False,
            details={"reason": "admin password check"},
        )
        form.password.errors.append("Your password is incorrect")
    return render_template("pages/admin/confirm_password.html", form=form, back=back)
