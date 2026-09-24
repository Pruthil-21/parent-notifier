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
