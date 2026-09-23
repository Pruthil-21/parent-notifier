import pytest

from parent_notifier import create_app
from parent_notifier.core.extensions import db


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture
def app_context(app):
    """For service and model tests. Route tests use `client`, which pushes its own context."""
    with app.app_context():
        yield


@pytest.fixture
def client(app):
    return app.test_client()
