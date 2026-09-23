from pathlib import Path

import pytest
from sqlalchemy import text

from parent_notifier import create_app
from parent_notifier.core.config import load_config
from parent_notifier.core.extensions import db


@pytest.fixture(autouse=True)
def no_database_override(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_testing_uses_in_memory_database():
    app = create_app("testing")
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"


def test_development_database_lives_in_instance_folder(tmp_path):
    url = load_config("development", tmp_path)["SQLALCHEMY_DATABASE_URI"]
    assert url == f"sqlite:///{Path(tmp_path, 'parent_notifier.db').as_posix()}"


def test_database_url_overrides_default(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://college-server/notifier")
    url = load_config("development", tmp_path)["SQLALCHEMY_DATABASE_URI"]
    assert url == "postgresql://college-server/notifier"


def test_sqlite_connections_enforce_foreign_keys(app_context):
    assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_constraints_get_predictable_names():
    naming = db.metadata.naming_convention
    assert naming["fk"] == "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
