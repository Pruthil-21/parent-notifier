import os

import pytest

from parent_notifier import create_app
from parent_notifier.core.extensions import db
from parent_notifier.services.accounts import credentials
from tests.factories.accounts import PASSWORD, make_mentor, sign_in

# A light scrypt setting keeps the suite fast; production uses full strength (a test in
# test_credentials checks the default).
credentials.HASH_METHOD = "scrypt:1024:8:1"


# Set TEST_DATABASE_URL to run the suite against Postgres (one test at a time: -n 0);
# otherwise each test gets its own in-memory SQLite database.
POSTGRES_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture
def app(tmp_path, monkeypatch):
    if POSTGRES_URL:
        monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    app = create_app("testing")
    # Runtime files go to a throwaway folder, never instance/.
    app.instance_path = str(tmp_path / "instance")
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        if POSTGRES_URL:
            db.session.remove()
            db.drop_all()
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


@pytest.fixture
def open_signup(app):
    """Sign-up starts off; tests of the create account page open it first."""
    from parent_notifier.services.accounts import registration

    with app.app_context():
        registration.set_signup_mode(registration.SIGNUP_OPEN)
