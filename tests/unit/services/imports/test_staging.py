from datetime import timedelta

import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.imports import StagedSheet
from parent_notifier.services.imports import staging
from parent_notifier.services.imports.sheet_parser import parse_sheet
from parent_notifier.services.shared import clock
from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor
from tests.factories.workbooks import sheet_rows

pytestmark = pytest.mark.usefixtures("app_context")


@pytest.fixture
def owner():
    mentor = make_mentor()
    class_group = make_class(mentor)
    return staging.Owner(mentor.id, class_group.id, make_semester(class_group, 4).id)


@pytest.fixture
def sheet():
    return parse_sheet([[str(value) for value in row] for row in sheet_rows()], 20)


def _tokens():
    return sorted(db.session.scalars(db.select(StagedSheet.token)))


def test_staged_sheet_comes_back_the_same(owner, sheet):
    token = staging.stage(owner, "sem4.xlsx", sheet)
    staged = staging.load(token, owner)
    assert (staged.filename, staged.sheet) == ("sem4.xlsx", sheet)
    assert len(token) == 32


@pytest.mark.parametrize("field", ["mentor_id", "class_id", "semester_id"])
def test_only_the_same_mentor_class_and_semester_can_load_it(owner, sheet, field):
    token = staging.stage(owner, "sem4.xlsx", sheet)
    other = staging.Owner(**(owner.__dict__ | {field: getattr(owner, field) + 100}))
    assert staging.load(token, other) is None


@pytest.mark.parametrize("token", ["", "../secret_key", "ABCDEF" * 6, "a" * 31, "a" * 32 + "/"])
def test_tokens_that_are_not_32_hex_characters_are_never_looked_up(owner, token):
    assert staging.load(token, owner) is None
    staging.discard(token)


def test_expired_import_is_not_loaded(owner, sheet, monkeypatch):
    token = staging.stage(owner, "sem4.xlsx", sheet)
    later = clock.now() + staging.MAX_AGE + timedelta(minutes=1)
    monkeypatch.setattr(clock, "now", lambda: later)
    assert staging.load(token, owner) is None


def test_discard_and_purge(owner, sheet, monkeypatch):
    now = clock.now()
    monkeypatch.setattr(clock, "now", lambda: now - timedelta(days=2))
    old = staging.stage(owner, "a.xlsx", sheet)
    monkeypatch.setattr(clock, "now", lambda: now)
    kept = staging.stage(owner, "b.xlsx", sheet)
    discarded = staging.stage(owner, "c.xlsx", sheet)
    staging.discard(discarded)
    assert old not in _tokens()  # staging a new sheet clears out stale ones
    assert _tokens() == [kept]


def test_deleting_the_semester_removes_its_staged_sheets(owner, sheet):
    from parent_notifier.models.academics import Semester

    staging.stage(owner, "sem4.xlsx", sheet)
    db.session.delete(db.session.get(Semester, owner.semester_id))
    db.session.commit()
    assert _tokens() == []
