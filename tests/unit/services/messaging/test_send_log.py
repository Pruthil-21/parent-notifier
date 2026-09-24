from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from parent_notifier.services.messaging import send_log
from parent_notifier.services.messaging.whatsapp_links import whatsapp_app_link, whatsapp_link
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor


def test_link_goes_to_whatsapp_web_with_the_text_encoded():
    text = "Dear Parent,\n1. DBMS: Theory – 86% & more?"  # noqa: RUF001
    link = whatsapp_link("+919000000101", text)
    parts = urlsplit(link)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "web.whatsapp.com", "/send")
    query = parse_qs(parts.query)
    assert query == {"phone": ["919000000101"], "text": [text]}
    assert " " not in link and "\n" not in link


def test_phone_link_opens_the_whatsapp_app_with_the_same_text():
    text = "Dear Parent,\nDBMS: 86% & more?"
    link = whatsapp_app_link("+919000000101", text)
    parts = urlsplit(link)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "wa.me", "/919000000101")
    assert parse_qs(parts.query) == {"text": [text]}


@pytest.mark.parametrize("make_link", [whatsapp_link, whatsapp_app_link])
def test_link_refuses_anything_but_digits(make_link):
    with pytest.raises(ValueError, match=r"\+91XXXXXXXXXX"):
        make_link("+91 90000 00101", "x")


@pytest.mark.usefixtures("app_context")
def test_marks_belong_to_the_current_round():
    mentor = make_mentor()
    class_group = make_class(mentor)
    semester = make_semester(class_group, 4, current_round=1, round_counter=1)
    student = make_student(class_group)
    send_log.record(semester, student.id, mentor.id, status="skipped", language="en")
    send_log.record(semester, student.id, mentor.id, status="sent", language="en")
    assert send_log.marks_for(semester)[student.id].status == "sent"
    semester.current_round = 2
    assert send_log.marks_for(semester) == {}


def test_labels():
    at = datetime(2026, 9, 23, 20, 0, tzinfo=UTC)
    assert send_log.label(send_log.Mark("sent", at), True, "Asia/Kolkata") == "Sent 24 Sep"
    assert send_log.label(send_log.Mark("skipped", at), True, "Asia/Kolkata") == "Skipped"
    assert send_log.label(None, True, "Asia/Kolkata") == "Pending"
    assert send_log.label(None, False, "Asia/Kolkata") == "No phone"
