import pytest

from parent_notifier.services.imports.compare import IdentityChange, compare
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.academics import make_class, make_student
from tests.factories.accounts import make_mentor
from tests.factories.workbooks import HEADER

pytestmark = pytest.mark.usefixtures("app_context")


def _sheet(*rows):
    return parse_sheet([HEADER[:5], *[[*row, "Theory=80"] for row in rows]], 20)


@pytest.fixture
def class_group():
    class_group = make_class(make_mentor())
    make_student(
        class_group,
        "23CE001",
        full_name="Avi Shah",
        parent_name="Mehul Shah",
        phone_raw="90000 00101",
        phone_e164="+919000000101",
    )
    return class_group


def test_new_and_existing_students_are_counted(class_group):
    result = compare(
        class_group,
        _sheet(
            ["23ce001", "Avi Shah", "Mehul Shah", "9000000101"],
            ["23CE002", "Riya Patel", "Kiran Patel", "9000000102"],
        ),
    )
    assert (result.new_students, result.existing_students) == (1, 1)
    assert result.changes == []


def test_differences_in_identity_are_listed(class_group):
    result = compare(class_group, _sheet(["23CE001", "Avi M. Shah", "Mehul Shah", "9000000199"]))
    assert result.changes == [
        IdentityChange("23CE001", "Student name", "Avi Shah", "Avi M. Shah"),
        IdentityChange("23CE001", "Phone", "90000 00101", "9000000199"),
    ]


def test_spacing_case_and_blanks_are_not_differences(class_group):
    result = compare(class_group, _sheet(["23CE001", "AVI SHAH", "", "+91 90000-00101"]))
    assert result.changes == []
