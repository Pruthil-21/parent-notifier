"""Registers every blueprint on the app."""

from flask import Flask

from parent_notifier.routes import help
from parent_notifier.routes.academics import class_settings, classes, home, semesters, students
from parent_notifier.routes.accounts import auth, profile, registration
from parent_notifier.routes.admin import users as admin_users
from parent_notifier.routes.imports import downloads, undo, upload
from parent_notifier.routes.messaging import send_log

BLUEPRINTS = (
    auth.bp,
    registration.bp,
    profile.bp,
    home.bp,
    classes.bp,
    semesters.bp,
    class_settings.bp,
    students.bp,
    upload.bp,
    undo.bp,
    downloads.bp,
    send_log.bp,
    help.bp,
    admin_users.bp,
)


def register_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
