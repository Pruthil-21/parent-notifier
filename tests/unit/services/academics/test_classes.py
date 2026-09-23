import pytest

from parent_notifier.services.academics import classes
from tests.factories.academics import make_class
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


@pytest.fixture
def owner():
    return make_mentor()


def test_create_class_saves_it_for_the_mentor(owner):
    class_group = classes.create_class(owner.id, "CE-A", "Computer Engineering", 2023)
    assert class_group.id is not None
    assert class_group.mentor_id == owner.id


def test_names_are_compared_ignoring_case_within_one_mentor(owner):
    make_class(owner, name="CE-A")
    other = make_mentor(username="niravshah", whatsapp_number="+919000000002")
    assert classes.name_taken(owner.id, "ce-a")
    assert not classes.name_taken(other.id, "CE-A")


def test_a_class_does_not_clash_with_itself(owner):
    class_group = make_class(owner, name="CE-A")
    assert not classes.name_taken(owner.id, "CE-A", except_class_id=class_group.id)


def test_exact_duplicate_at_save_time_raises(owner):
    make_class(owner, name="CE-A")
    with pytest.raises(classes.ClassNameTakenError):
        classes.create_class(owner.id, "CE-A", "Computer Engineering", 2024)


def test_update_details_and_rules(owner):
    class_group = make_class(owner)
    classes.update_details(class_group, "CE-A2", "Information Technology", 2024)
    classes.update_rules(class_group, 80, 12, 30)
    assert (class_group.name, class_group.admission_year) == ("CE-A2", 2024)
    assert (class_group.attendance_threshold, class_group.midsem_pass_mark) == (80, 12)


def test_renaming_onto_an_existing_name_raises(owner):
    make_class(owner, name="CE-B")
    class_group = make_class(owner, name="CE-A")
    with pytest.raises(classes.ClassNameTakenError):
        classes.update_details(class_group, "CE-B", "Computer Engineering", 2023)
