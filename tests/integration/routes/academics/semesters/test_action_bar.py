import re

import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Student
from parent_notifier.services.messaging import send_log
from tests.factories.academics import import_sheet, make_class, make_semester


@pytest.fixture
def places(app, mentor):
    """Sem 4 has a sheet with parents pending; Sem 5 has no sheet yet."""
    with app.app_context():
        class_group = make_class(mentor)
        sem4 = make_semester(class_group, 4)
        import_sheet(class_group, sem4, mentor.id)
        make_semester(class_group, 5)
        return f"/classes/{class_group.id}/sem/4", f"/classes/{class_group.id}/sem/5", sem4.id


def action_bar(html: str) -> str:
    """The bar's markup, with the Sheet menu folded into a "[Sheet]" marker."""
    bar = html[html.index('<div class="action-bar">') :]
    bar = re.sub(r"<details.*?</details>", "[Sheet]", bar, count=1, flags=re.S)
    return bar[: bar.index("</div>")]


def buttons(html: str) -> list[str]:
    """The labels of the bar's buttons in order; the Sheet menu counts as one."""
    labels = re.findall(
        r'class="button[^"]*"[^>]*>(?:<svg.*?</svg>)?([^<]+)<|(\[Sheet\])', action_bar(html), re.S
    )
    return [text.strip() or menu for text, menu in labels]


def test_messaging_comes_first_and_the_sheet_commands_share_one_menu(signed_in_client, places):
    sem4, _, _ = places
    html = signed_in_client.get(sem4).get_data(as_text=True)
    assert buttons(html) == [
        "Message pending parents (4)",
        "[Sheet]",
        "Add student",
        "Class settings",
    ]
    menu = re.search(r'<details class="menu sheet-menu".*?</details>', html, re.S).group(0)
    items = re.findall(r'class="menu__item(?: [^"]*)?"[^>]*>\s*(?:<span>)?([^<]+)<', menu)
    assert [item.strip() for item in items] == [
        "Upload sheet",
        "Download current data",
        "Sheet format",
        "Undo last import",
    ]
    assert 'data-dialog-open="upload-sheet"' in menu and 'data-dialog-open="undo-import"' in menu


def test_before_the_first_sheet_upload_is_the_main_button(signed_in_client, places):
    _, sem5, _ = places
    html = signed_in_client.get(sem5).get_data(as_text=True)
    assert buttons(html) == ["Upload sheet", "[Sheet]", "Add student", "Class settings"]
    assert "button--primary" in action_bar(html).split("Upload sheet")[0]
    assert "Undo last import" not in html


def test_once_every_parent_is_done_there_is_no_main_button(app, mentor, signed_in_client, places):
    sem4, _, semester_id = places
    with app.app_context():
        from parent_notifier.models.academics import Semester

        semester = db.session.get(Semester, semester_id)
        for student in db.session.scalars(db.select(Student)):
            send_log.record(
                semester,
                student.id,
                mentor.id,
                status="skipped",
                note="",
                message="",
            )
    html = signed_in_client.get(sem4).get_data(as_text=True)
    assert buttons(html) == ["[Sheet]", "Add student", "Class settings"]
