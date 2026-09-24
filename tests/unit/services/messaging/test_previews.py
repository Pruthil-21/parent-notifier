from parent_notifier.services.academics.views.risk import SubjectResult
from parent_notifier.services.academics.views.semester_view import StudentRow
from parent_notifier.services.messaging import previews

CONFIG = {"COLLEGE_NAME": "GCET", "COLLEGE_NAME_GU": "જી.સી.ઈ.ટી."}
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


def test_both_languages_come_plain_and_with_a_note_marker():
    context = previews.context_for(4, 20, "Asha Patel", CONFIG)
    messages = previews.messages_for(ROW, context)
    assert set(messages) == {"en", "gu"}
    assert previews.NOTE_MARKER not in messages["en"]["plain"]
    assert f"Note from the mentor: {previews.NOTE_MARKER}" in messages["en"]["withNote"]
    assert messages["en"]["plain"].endswith("Prof. Asha Patel\nGCET")
    assert messages["gu"]["plain"].endswith("પ્રો. Asha Patel\nજી.સી.ઈ.ટી.")
    assert "Sem 4" in messages["en"]["plain"]
