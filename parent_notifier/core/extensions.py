"""Flask extensions, created unbound here and attached to the app in create_app()."""

import sqlite3
from pathlib import Path

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

# Named constraints let Alembic rebuild SQLite tables without guessing names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


db = SQLAlchemy(model_class=Base)
# Batch mode: SQLite cannot ALTER most constraints in place, so Alembic copies the table.
migrate = Migrate(render_as_batch=True)
csrf = CSRFProtect()
# No default limits: only the routes that check secrets or can be hammered opt in.
limiter = Limiter(key_func=get_remote_address)
login_manager = LoginManager()
login_manager.login_view = "auth.sign_in"
# Landing on the sign-in page already says what to do; a flashed line would only repeat it.
login_manager.login_message = None
# "strong" would sign mentors out whenever the college Wi-Fi hands them a new IP address.
login_manager.session_protection = "basic"


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite ignores foreign keys unless each connection switches them on."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


def init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db, directory=str(MIGRATIONS_DIR))
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
