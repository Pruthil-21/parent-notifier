"""Registers every blueprint on the app."""

from flask import Flask

from parent_notifier.routes.academics import class_settings, classes, home, semesters
from parent_notifier.routes.accounts import auth, profile, registration
from parent_notifier.routes.imports import downloads, undo, upload

BLUEPRINTS = (
    auth.bp,
    registration.bp,
    profile.bp,
    home.bp,
    classes.bp,
    semesters.bp,
    class_settings.bp,
    upload.bp,
    undo.bp,
    downloads.bp,
)


def register_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
