"""Registers every blueprint on the app."""

from flask import Flask

from parent_notifier.routes.academics import home
from parent_notifier.routes.accounts import auth, registration

BLUEPRINTS = (auth.bp, registration.bp, home.bp)


def register_blueprints(app: Flask) -> None:
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
