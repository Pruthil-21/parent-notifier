"""The Vercel entry point and build step."""

import importlib
import importlib.util
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def build(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "vercel_build", ROOT / "scripts" / "deploy" / "vercel_build.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("FLASK_CONFIG", "testing")
    for name in ("DATABASE_URL", "RUN_MIGRATIONS", "VERCEL_ENV"):
        monkeypatch.delenv(name, raising=False)
    return module


def test_entry_point_builds_the_app_from_the_environment(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "testing")
    wsgi = importlib.reload(importlib.import_module("parent_notifier.wsgi"))
    assert isinstance(wsgi.app, Flask)
    assert wsgi.app.config["ENV_NAME"] == "testing"


def test_migrations_bring_the_database_up_to_date(build, monkeypatch, tmp_path):
    url = f"sqlite:///{(tmp_path / 'deploy.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    build.migrate()
    engine = create_engine(url)
    assert {"mentors", "staged_sheets", "alembic_version"} <= set(inspect(engine).get_table_names())
    engine.dispose()


def test_migrations_need_a_database_address_unless_switched_off(build, monkeypatch):
    with pytest.raises(SystemExit, match="DATABASE_URL is not set"):
        build.migrate()
    monkeypatch.setenv("RUN_MIGRATIONS", "false")
    build.migrate()


def test_a_preview_build_leaves_the_live_database_alone(build, monkeypatch, tmp_path):
    database = tmp_path / "live.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database.as_posix()}")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    build.migrate()
    assert not database.exists()


def test_a_serverless_start_skips_the_migration_tool(monkeypatch):
    from parent_notifier import create_app

    monkeypatch.setenv("VERCEL", "1")
    assert "migrate" not in create_app("testing").extensions
    monkeypatch.delenv("VERCEL")
    assert "migrate" in create_app("testing").extensions
