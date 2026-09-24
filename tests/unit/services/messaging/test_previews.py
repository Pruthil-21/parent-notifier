from types import SimpleNamespace

from parent_notifier.services.academics.views.risk import SubjectResult
from parent_notifier.services.academics.views.semester_view import StudentRow
from parent_notifier.services.messaging import previews

CONFIG = {"COLLEGE_NAME": "GCET"}
ROW = StudentRow(
    id=1,
    enrollment_no="23CE001",
    full_name="Avi Shah",
    parent_name="Mehul Shah",
    phone_raw="9000000101",
    phone_e164="+919000000101",
    status="active",
    band="doing_well",
    results=[SubjectResult("DBMS", theory=86, marks=16)],
    shortages=[],
    fails=[],
    lowest=None,
    average=16,
)


def test_the_message_comes_plain_and_with_a_note_marker():
    semester = SimpleNamespace(number=4, attendance_from=None, attendance_to=None)
    context = previews.context_for(semester, 20, "Asha Patel", CONFIG)
    messages = previews.messages_for(ROW, context)
    assert set(messages) == {"plain", "withNote"}
    assert previews.NOTE_MARKER not in messages["plain"]
    assert f"Note from the mentor / મેન્ટરની નોંધ: {previews.NOTE_MARKER}" in messages["withNote"]
    assert messages["plain"].endswith("Prof. Asha Patel\nGCET")
    assert "Sem 4" in messages["plain"] and "સેમ 4" in messages["plain"]
