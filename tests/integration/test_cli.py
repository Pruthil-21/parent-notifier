from pathlib import Path

import pytest
from sqlalchemy import func, select

from parent_notifier import create_app
from parent_notifier.core.cli import DEMO_PASSWORD, DEMO_USERNAME, SAMPLES
from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Student
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.imports.sheet_parser import parse_sheet
from parent_notifier.services.imports.sheet_reader import read_sheet
from tests.factories.accounts import sign_in


@pytest.mark.parametrize("path", sorted(Path(SAMPLES).glob("*.xlsx")), ids=lambda path: path.name)
def test_samples_are_clean_and_fictional(path):
    sheet = parse_sheet(read_sheet(path.name, path.read_bytes()), 20)
    assert sheet.errors == []
    assert sheet.ignored_columns == ["Sr No"]
    assert len(sheet.rows) == 20
    assert all(row.phone_e164.startswith("+9190000") for row in sheet.rows)


def test_seed_demo_builds_the_demo_class(app):
    result = app.test_cli_runner().invoke(args=["seed-demo"])
    assert result.exit_code == 0, result.output
    assert "Imported Sem 6: 20 students" in result.output
    with app.app_context():
        mentor = db.session.scalar(select(Mentor).where(Mentor.username == DEMO_USERNAME))
        class_group = db.session.scalar(select(ClassGroup).where(ClassGroup.mentor_id == mentor.id))
        assert [s.number for s in class_group.semesters] == [6, 7]
        assert all(len(s.students) == 20 for s in class_group.semesters)
    assert sign_in(app.test_client(), DEMO_USERNAME, DEMO_PASSWORD).status_code == 302


def test_seed_demo_twice_replaces_rather_than_duplicates(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed-demo"])
    assert runner.invoke(args=["seed-demo"]).exit_code == 0
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Mentor)) == 1
        assert db.session.scalar(select(func.count()).select_from(Student)) == 20


def test_seed_demo_refuses_to_run_in_production(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "production-test-key")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'prod.db').as_posix()}")
    app = create_app("production")
    result = app.test_cli_runner().invoke(args=["seed-demo"])
    assert result.exit_code != 0
    assert "seed-demo only runs outside production" in result.output
