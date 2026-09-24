import io
import re

from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import SemesterSubject
from tests.factories.academics import make_class, make_semester
from tests.factories.workbooks import make_xlsx, sheet_rows

ROW = [
    "23CE001",
    "Avi Shah",
    "Mehul Shah",
    "90000 00101",
    "Theory=90,Marks=16",
    "Theory=90,Marks=8/25",
]


def _import(client, base, rows):
    data = {"sheet": (io.BytesIO(make_xlsx(sheet_rows(rows=rows))), "sem4.xlsx")}
    html = client.post(f"{base}/import", data=data, content_type="multipart/form-data")
    token = re.search(r'name="token" value="([0-9a-f]{32})"', html.get_data(as_text=True))
    client.post(f"{base}/import/confirm", data={"token": token.group(1)})


def _totals(app):
    with app.app_context():
        rows = db.session.execute(select(SemesterSubject.name, SemesterSubject.midsem_max))
        return dict(rows.all())


def test_a_subject_out_of_25_is_saved_judged_messaged_and_undone(app, signed_in_client, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        make_semester(class_group, 4)
        base = f"/classes/{class_group.id}/sem/4"
    _import(signed_in_client, base, [ROW])
    assert _totals(app) == {"DBMS": None, "OS": 25}
    page = signed_in_client.get(base).get_data(as_text=True)
    assert "OS 8/25" in page  # below 35% of 25, so it needs attention
    assert r"Mid-Sem \u2013 8/25" in page  # the message, as the page embeds it
    _import(signed_in_client, base, [[*ROW[:5], "Theory=91,Marks=12"]])
    assert _totals(app) == {"DBMS": None, "OS": None}  # plain marks: out of the class's 20
    signed_in_client.post(f"{base}/import/undo")
    assert _totals(app) == {"DBMS": None, "OS": 25}
