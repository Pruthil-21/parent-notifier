"""Command-line tasks: `flask seed-demo` resets the demo account, and `flask create-admin`
creates the one admin account. No page in the app can make anyone an admin."""

from pathlib import Path

import click
from flask import Flask, current_app
from flask.cli import with_appcontext
from sqlalchemy import exists, select
from werkzeug.datastructures import MultiDict

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
DEMO_USERNAME = "pruthilmistry"
# A known password for the local demo only; the command refuses to run in production.
DEMO_PASSWORD = "Demo@2026"  # noqa: S105
DEMO_SEMESTERS = (6, 7)


def _import_sample(class_group, mentor, number: int) -> int:
    from parent_notifier.services.academics.records import semesters
    from parent_notifier.services.imports.apply import apply_import
    from parent_notifier.services.imports.sheet_parser import parse_sheet
    from parent_notifier.services.imports.sheet_reader import read_sheet

    semester, _ = semesters.add_semester(class_group, number)
    path = SAMPLES / f"ce-a-sem-{number}.xlsx"
    sheet = parse_sheet(read_sheet(path.name, path.read_bytes()), class_group.midsem_max)
    if sheet.errors:
        raise click.ClickException(f"{path.name} has problems: {sheet.errors[0]}")
    apply_import(class_group, semester, mentor.id, path.name, sheet, update_identity=False)
    return len(sheet.rows)


@click.command("seed-demo")
@with_appcontext
def seed_demo() -> None:
    """Replace the demo mentor with a fresh one holding class CE-A and two semesters."""
    # Imported here so the command's needs don't slow down every start of the app.
    from parent_notifier.services.academics.records import classes
    from parent_notifier.services.accounts import registration

    if current_app.config["ENV_NAME"] == "production":
        raise click.ClickException("seed-demo only runs outside production.")
    existing = db.session.scalar(select(Mentor).where(Mentor.username == DEMO_USERNAME))
    if existing is not None:
        db.session.delete(existing)
        db.session.commit()
    mentor, _code = registration.create_mentor(
        "Pruthil Mistry", DEMO_USERNAME, "90000 00000", DEMO_PASSWORD
    )
    class_group = classes.create_class(mentor.id, "CE-A", "Computer Engineering", 2023)
    for number in DEMO_SEMESTERS:
        count = _import_sample(class_group, mentor, number)
        click.echo(f"Imported Sem {number}: {count} students")
    click.echo(f"Demo ready. Sign in as {DEMO_USERNAME} with password {DEMO_PASSWORD}")


@click.command("create-admin")
@click.option("--name", required=True, help="Full name, as messages are signed")
@click.option("--username", required=True)
@click.option("--phone", required=True, help="The WhatsApp number, like 98765 43210")
@click.option("--department", required=True)
@click.password_option(help="Asked for twice, without showing it")
@with_appcontext
def create_admin(name: str, username: str, phone: str, department: str, password: str) -> None:
    """Create the admin account. There is one admin, so this refuses if one exists."""
    from parent_notifier.forms.accounts import CreateAccountForm
    from parent_notifier.services.accounts import registration

    if db.session.scalar(select(exists().where(Mentor.role == "admin"))):
        raise click.ClickException("An admin account already exists.")
    # The same checks as the create account page, so the admin follows the same rules.
    fields = {"full_name": name, "username": username, "whatsapp_number": phone}
    form = CreateAccountForm(
        formdata=MultiDict(fields | {"department": department, "password": password}),
        meta={"csrf": False},
    )
    if not form.validate():
        problems = "; ".join(error for errors in form.errors.values() for error in errors)
        raise click.ClickException(problems)
    mentor, code = registration.create_mentor(
        form.full_name.data,
        form.username.data,
        form.whatsapp_number.data,
        form.password.data,
        form.department.data,
        role="admin",
    )
    click.echo(f"Admin account created for {mentor.username}.")
    click.echo(f"Recovery code, shown only now: {code}")


def init_cli(app: Flask) -> None:
    app.cli.add_command(seed_demo)
    app.cli.add_command(create_admin)
