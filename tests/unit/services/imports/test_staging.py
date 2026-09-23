import os
from datetime import timedelta

import pytest

from parent_notifier.services.imports import staging
from parent_notifier.services.imports.sheet_parser import parse_sheet
from parent_notifier.services.shared import clock
from tests.factories.workbooks import sheet_rows

OWNER = staging.Owner(mentor_id=1, class_id=2, semester_id=3)


@pytest.fixture
def sheet():
    return parse_sheet([[str(value) for value in row] for row in sheet_rows()], 20)


def test_staged_sheet_comes_back_the_same(tmp_path, sheet):
    token = staging.stage(tmp_path, OWNER, "sem4.xlsx", sheet)
    staged = staging.load(tmp_path, token, OWNER)
    assert (staged.filename, staged.sheet) == ("sem4.xlsx", sheet)
    assert len(token) == 32


@pytest.mark.parametrize(
    "other",
    [
        staging.Owner(mentor_id=9, class_id=2, semester_id=3),
        staging.Owner(mentor_id=1, class_id=9, semester_id=3),
        staging.Owner(mentor_id=1, class_id=2, semester_id=9),
    ],
)
def test_only_the_same_mentor_class_and_semester_can_load_it(tmp_path, sheet, other):
    token = staging.stage(tmp_path, OWNER, "sem4.xlsx", sheet)
    assert staging.load(tmp_path, token, other) is None


@pytest.mark.parametrize("token", ["", "../secret_key", "ABCDEF" * 6, "a" * 31, "a" * 32 + "/"])
def test_tokens_that_are_not_32_hex_characters_are_never_used_as_paths(tmp_path, token):
    assert staging.load(tmp_path, token, OWNER) is None
    staging.discard(tmp_path, token)


def test_expired_import_is_not_loaded(tmp_path, sheet, monkeypatch):
    token = staging.stage(tmp_path, OWNER, "sem4.xlsx", sheet)
    later = clock.now() + staging.MAX_AGE + timedelta(minutes=1)
    monkeypatch.setattr(clock, "now", lambda: later)
    assert staging.load(tmp_path, token, OWNER) is None


def test_discard_and_purge(tmp_path, sheet):
    kept = staging.stage(tmp_path, OWNER, "a.xlsx", sheet)
    old = staging.stage(tmp_path, OWNER, "b.xlsx", sheet)
    discarded = staging.stage(tmp_path, OWNER, "c.xlsx", sheet)
    staging.discard(tmp_path, discarded)
    two_days_ago = (clock.now() - timedelta(days=2)).timestamp()
    os.utime(tmp_path / f"{old}.json", (two_days_ago, two_days_ago))
    staging.purge_old(tmp_path)
    assert sorted(path.stem for path in tmp_path.iterdir()) == [kept]
