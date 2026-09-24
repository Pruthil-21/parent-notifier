import os

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text

from parent_notifier import create_app
from parent_notifier.core.extensions import db


def test_migrations_match_the_models_and_downgrade_cleanly(tmp_path, monkeypatch):
    sqlite = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", os.environ.get("TEST_DATABASE_URL", sqlite))
    app = create_app("testing")
    with app.app_context():
        upgrade()
        with db.engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            assert compare_metadata(context, db.metadata) == []
            if connection.dialect.name == "postgresql":
                assert _tables_without_row_level_security(connection) == []
                _check_activity_log_is_append_only(connection)
        downgrade(revision="base")
        assert inspect(db.engine).get_table_names() == ["alembic_version"]
        db.engine.dispose()


def _tables_without_row_level_security(connection) -> list[str]:
    """Every table must have row-level security on Postgres, so a host's web API such
    as Supabase's can't read it. A new table needs it switched on in its migration."""
    query = text(
        "SELECT relname FROM pg_class JOIN pg_namespace ON pg_namespace.oid = relnamespace "
        "WHERE nspname = current_schema() AND relkind = 'r' AND NOT relrowsecurity"
    )
    return sorted(connection.execute(query).scalars())


def _check_activity_log_is_append_only(connection) -> None:
    """Postgres refuses edits and recent deletes, yet deleting an account still works."""
    import pytest
    from sqlalchemy.exc import DBAPIError

    connection.execute(
        text(
            "INSERT INTO mentors (full_name, username, whatsapp_number, password_hash,"
            " recovery_code_hash, created_at, updated_at) VALUES ('A', 'a', '+919000000001',"
            " 'x', 'x', now(), now())"
        )
    )
    connection.execute(
        text(
            "INSERT INTO activity_log (created_at, category, event, succeeded, actor_id)"
            " SELECT now(), 'security', 'sign_in', true, id FROM mentors"
        )
    )
    for statement in ("UPDATE activity_log SET event = 'x'", "DELETE FROM activity_log"):
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError, match=r"(?i)activity log"):
            connection.execute(text(statement))
        savepoint.rollback()
    connection.execute(text("DELETE FROM mentors"))
    assert connection.execute(text("SELECT actor_id FROM activity_log")).scalar() is None
    connection.rollback()
