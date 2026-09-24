import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Student
from parent_notifier.services.academics.views import home_summary
from parent_notifier.services.messaging import send_log
from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


@pytest.fixture
def owner():
    return make_mentor()


@pytest.fixture
def ce_a(owner):
    """Sem 3 and Sem 4 imported; in Sem 4 one parent is messaged and one student has left."""
    class_group = make_class(owner, name="CE-A")
    import_sheet(class_group, make_semester(class_group, 3), owner.id)
    sem4 = make_semester(class_group, 4)
    import_sheet(class_group, sem4, owner.id)
    db.session.scalars(db.select(Student).filter_by(enrollment_no="23CE004")).one().status = "left"
    db.session.commit()
    first = db.session.scalars(db.select(Student).filter_by(enrollment_no="23CE002")).one()
    send_log.record(sem4, first.id, owner.id, status="sent", note="", message="")
    return class_group


def test_each_class_counts_from_its_latest_semester(owner, ce_a):
    row = home_summary.build(owner.id).classes[0]
    assert row.semester.number == 4
    assert (row.students, row.at_risk, row.pending) == (3, 1, 2)
    assert row.last_imported_at is not None


def test_classes_without_a_sheet_or_semester(owner, ce_a):
    ce_b = make_class(owner, name="ce-b")
    make_semester(ce_b, 1)
    make_class(owner, name="CE-C")
    summary = home_summary.build(owner.id)
    assert [row.class_group.name for row in summary.classes] == ["CE-A", "ce-b", "CE-C"]
    empty, bare = summary.classes[1:]
    assert (empty.semester.number, empty.students, empty.last_imported_at) == (1, 0, None)
    assert (bare.semester, bare.students, bare.last_imported_at) == (None, 0, None)
    assert [(s.class_group.name, s.number) for s in summary.waiting] == [("ce-b", 1)]


def test_totals_and_the_one_class_behind_a_figure(owner, ce_a):
    other = make_class(owner, name="CE-B")
    import_sheet(
        other,
        make_semester(other, 2),
        owner.id,
        rows=[
            ["23CE101", "Dev Rana", "Jay Rana", "9000000111", "Theory=95", "Theory=96"],
        ],
    )
    summary = home_summary.build(owner.id)
    assert (summary.at_risk, summary.pending) == (1, 3)
    assert summary.only("at_risk").class_group.name == "CE-A"
    assert summary.only("pending") is None


def test_other_mentors_classes_are_left_out(owner, ce_a):
    stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
    make_semester(make_class(stranger, name="IT-A"), 1)
    summary = home_summary.build(stranger.id)
    assert [row.class_group.name for row in summary.classes] == ["IT-A"]
    assert len(summary.waiting) == 1
    assert home_summary.build(owner.id).waiting == []
