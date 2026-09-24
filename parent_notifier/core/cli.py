"""Command-line tasks for developers: `flask seed-demo` resets the demo account."""

from pathlib import Path

import click
from flask import Flask, current_app
from flask.cli import with_appcontext
from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.academics.records import classes, semesters
from parent_notifier.services.accounts import registration
from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from parent_notifier.services.imports.sheet_reader import read_sheet

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
DEMO_USERNAME = "pruthilmistry"
# A known password for the local demo only; the command refuses to run in production.
DEMO_PASSWORD = "Demo@2026"  # noqa: S105
DEMO_SEMESTERS = (6, 7)


def _import_sample(class_group, mentor, number: int) -> int:
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


def init_cli(app: Flask) -> None:
    app.cli.add_command(seed_demo)
