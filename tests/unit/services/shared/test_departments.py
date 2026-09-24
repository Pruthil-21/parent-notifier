import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.college import DEFAULT_DEPARTMENTS, Department
from parent_notifier.services.shared import departments
from tests.factories.academics import make_class
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


def _department(name):
    return db.session.scalars(db.select(Department).filter_by(name=name)).one()


def test_a_new_database_starts_with_the_colleges_departments():
    assert departments.names() == sorted(DEFAULT_DEPARTMENTS)
    assert departments.canonical("  computer   ENGINEERING ") == "Computer Engineering"
    assert departments.canonical("Physics") is None


def test_renaming_updates_every_mentor_and_class():
    mentor = make_mentor(department="Computer Engineering")
    class_group = make_class(mentor, department="Computer Engineering")
    departments.rename(_department("Computer Engineering"), "Computer Engg")
    db.session.refresh(mentor)
    db.session.refresh(class_group)
    assert (mentor.department, class_group.department) == ("Computer Engg", "Computer Engg")
    assert departments.usage("Computer Engg") == (1, 1)


def test_a_department_in_use_cannot_be_removed():
    make_class(make_mentor(), department="Civil Engineering")
    with pytest.raises(departments.DepartmentInUseError):
        departments.remove(_department("Civil Engineering"))
    departments.remove(_department("Chemical Engineering"))
    assert "Chemical Engineering" not in departments.names()
