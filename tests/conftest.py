import pytest

from parent_notifier import create_app
from parent_notifier.core.extensions import db
from tests.factories.accounts import PASSWORD, make_mentor, sign_in


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.engine.dispose()


@pytest.fixture
def app_context(app):
    """For service and model tests. Route tests use `client`, which pushes its own context."""
    with app.app_context():
        yield


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def mentor(app):
    """A mentor who signs in as "ashapatel" with the factory password."""
    with app.app_context():
        mentor = make_mentor(password=PASSWORD)
        db.session.refresh(mentor)
        db.session.expunge(mentor)
    return mentor


@pytest.fixture
def signed_in_client(client, mentor):
    sign_in(client)
    return client
