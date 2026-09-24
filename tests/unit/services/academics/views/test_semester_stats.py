import pytest
from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import SemesterStats, Student
from parent_notifier.services.academics.records import classes, students
from parent_notifier.services.academics.views import home_summary, semester_stats
from parent_notifier.services.messaging import send_log
from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


@pytest.fixture
def setup():
    mentor = make_mentor()
    class_group = make_class(mentor)
    semester = make_semester(class_group, 4)
    import_sheet(class_group, semester, mentor.id)
    return mentor, class_group, semester


def _counts(semester):
    return semester_stats.counts_for([semester])[semester.id]


def test_counts_match_the_semester_page_and_are_kept(setup):
    mentor, _, semester = setup
    row = home_summary.build(mentor.id).classes[0]
    assert _counts(semester) == semester_stats.Counts(row.students, row.at_risk, row.pending)
    assert db.session.get(SemesterStats, semester.id) is not None


def test_every_change_that_moves_the_counts_clears_them(setup):
    mentor, class_group, semester = setup
    assert _counts(semester).pending == 4
    avi = db.session.scalars(select(Student).filter_by(enrollment_no="23CE001")).one()
    send_log.record(semester, avi.id, mentor.id, status="sent", note="", message="")
    assert _counts(semester).pending == 3
    details = {"full_name": avi.full_name, "parent_name": avi.parent_name, "phone": avi.phone_raw}
    students.update_student(avi, details | {"status": "left"})
    assert (_counts(semester).students, _counts(semester).at_risk) == (3, 0)
    classes.update_rules(class_group, 90, 7, 20)
    assert _counts(semester).at_risk == 1  # the test sheet's 88% in OS is now a shortage
