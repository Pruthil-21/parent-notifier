from datetime import UTC, datetime

import pytest

from parent_notifier.services.academics.records import ownership
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


@pytest.fixture
def owner():
    return make_mentor()


@pytest.fixture
def stranger():
    return make_mentor(username="niravshah", whatsapp_number="+919000000002")


def test_a_mentor_finds_only_their_own_class(owner, stranger):
    class_group = make_class(owner)
    assert ownership.get_class(owner.id, class_group.id) == class_group
    assert ownership.get_class(stranger.id, class_group.id) is None
    assert ownership.get_class(owner.id, 999) is None


def test_list_shows_latest_semester_active_students_and_last_sheet(owner):
    class_group = make_class(owner)
    make_semester(class_group, 3, last_imported_at=datetime(2026, 1, 10, tzinfo=UTC))
    make_semester(class_group, 4, last_imported_at=datetime(2026, 7, 20, tzinfo=UTC))
    make_student(class_group, "23CE001")
    make_student(class_group, "23CE002")
    make_student(class_group, "23CE003", status="left")
    [row] = ownership.list_classes(owner.id)
    assert row.class_group == class_group
    assert row.latest_semester == 4
    assert row.active_students == 2
    assert row.last_imported_at == datetime(2026, 7, 20, tzinfo=UTC)


def test_class_without_semesters_or_students(owner):
    make_class(owner)
    [row] = ownership.list_classes(owner.id)
    assert (row.latest_semester, row.active_students, row.last_imported_at) == (None, 0, None)


def test_lists_are_sorted_by_name_and_hold_only_the_mentors_classes(owner, stranger):
    for name in ("ce-b", "CE-A", "IT-A"):
        make_class(owner, name=name)
    make_class(stranger, name="AA-1")
    assert [row.class_group.name for row in ownership.list_classes(owner.id)] == [
        "CE-A",
        "ce-b",
        "IT-A",
    ]
    assert [name for _id, name in ownership.class_links(owner.id)] == ["CE-A", "ce-b", "IT-A"]
