from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect

from parent_notifier import create_app
from parent_notifier.core.extensions import db


def test_migrations_match_the_models_and_downgrade_cleanly(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}")
    app = create_app("testing")
    with app.app_context():
        upgrade()
        with db.engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            assert compare_metadata(context, db.metadata) == []
        downgrade(revision="base")
        assert inspect(db.engine).get_table_names() == ["alembic_version"]
        db.engine.dispose()
