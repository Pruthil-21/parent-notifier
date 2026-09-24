import pytest
from werkzeug.datastructures import MultiDict

from parent_notifier.forms.academics import EditStudentForm
from parent_notifier.forms.accounts import full_name_field
from parent_notifier.forms.admin import AnnouncementForm, DepartmentForm


@pytest.mark.parametrize(
    ("form_class", "field"),
    [
        (EditStudentForm, "full_name"),
        (type("NameForm", (DepartmentForm,), {"full_name": full_name_field()}), "full_name"),
        (DepartmentForm, "name"),
        (AnnouncementForm, "text"),
    ],
)
def test_text_of_only_spaces_counts_as_missing(app, form_class, field):
    with app.test_request_context():
        form = form_class(formdata=MultiDict({field: "  \t "}), meta={"csrf": False})
        form.validate()
        assert field in form.errors
