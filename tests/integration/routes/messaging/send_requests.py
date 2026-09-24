"""Calls the messaging tests make: logging a send and reading what was stored."""

import json
import re

from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.messaging import SendLog

HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS"]
ROWS = [
    ["23CE001", "Avi Shah", "Mehul Shah", "9000000101", "Theory=86,Marks=16"],
    ["23CE002", "Riya Patel", "Kiran Patel", "123", "Theory=70"],
]


def log(client, base, student_id, **body):
    payload = {"status": "sent", "note": ""} | body
    return client.post(f"{base}/students/{student_id}/log", json=payload)


def entries(app):
    with app.app_context():
        return db.session.scalars(select(SendLog)).all()


def students_data(html):
    block = re.search(r'id="students-data">(.*?)</script>', html, re.S)
    return json.loads(block.group(1))
