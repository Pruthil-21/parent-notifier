import io
import re
from datetime import date

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Semester
from tests.factories.academics import make_class, make_semester
from tests.factories.workbooks import make_xlsx


def _upload(client, base, **dates):
    data = {"sheet": (io.BytesIO(make_xlsx()), "sem4.xlsx")} | dates
    return client.post(f"{base}/import", data=data, content_type="multipart/form-data")


def _import(client, base, **dates):
    html = _upload(client, base, **dates).get_data(as_text=True)
    token = re.search(r'name="token" value="([0-9a-f]{32})"', html).group(1)
    client.post(f"{base}/import/confirm", data={"token": token})


def _period(app, semester_id):
    with app.app_context():
        semester = db.session.get(Semester, semester_id)
        return semester.attendance_from, semester.attendance_to


def test_the_attendance_period_is_saved_shown_and_undone(app, signed_in_client, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        semester_id = make_semester(class_group, 4).id
        base = f"/classes/{class_group.id}/sem/4"
    _import(signed_in_client, base, attendance_from="2026-07-07", attendance_to="2026-09-18")
    assert _period(app, semester_id) == (date(2026, 7, 7), date(2026, 9, 18))
    page = signed_in_client.get(base).get_data(as_text=True)
    assert "attendance 07-07-26 to 18-09-26" in page
    assert "for Sem 4, from 07-07-26 to 18-09-26." in page  # in the popup's message
    assert 'value="2026-07-07"' in page  # the next upload starts from it

    _import(signed_in_client, base, attendance_from="2026-07-07", attendance_to="2026-10-30")
    signed_in_client.post(f"{base}/import/undo")
    assert _period(app, semester_id) == (date(2026, 7, 7), date(2026, 9, 18))
    _import(signed_in_client, base)  # a sheet without dates keeps the period
    assert _period(app, semester_id) == (date(2026, 7, 7), date(2026, 9, 18))


def test_half_a_period_or_one_ending_before_it_starts_is_refused(signed_in_client, app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        make_semester(class_group, 4)
        base = f"/classes/{class_group.id}/sem/4"
    one_end = _upload(signed_in_client, base, attendance_from="2026-07-07").get_data(as_text=True)
    assert "Enter both attendance dates, or leave both empty" in one_end
    backwards = _upload(
        signed_in_client, base, attendance_from="2026-09-18", attendance_to="2026-07-07"
    ).get_data(as_text=True)
    assert "The attendance period must end on or after it starts" in backwards
