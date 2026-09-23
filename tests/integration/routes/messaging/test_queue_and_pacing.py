from parent_notifier.core.extensions import db
from tests.integration.routes.messaging.send_requests import entries as _entries
from tests.integration.routes.messaging.send_requests import log as _log
from tests.integration.routes.messaging.send_requests import students_data as _data


def test_queue_button_counts_pending_parents_and_falls_back_to_a_filter(signed_in_client, setup):
    base, ids = setup
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "Message pending parents (1)" in html
    assert f'href="{base}?status=pending">Message pending parents' in html
    pending_page = signed_in_client.get(f"{base}?status=pending").get_data(as_text=True)
    assert "Showing 1 of 2 students" in pending_page
    avi = next(s for s in _data(html) if s["id"] == ids["23CE001"])
    assert avi["pending"] is True


def test_queue_button_goes_once_everyone_is_done(signed_in_client, setup):
    base, ids = setup
    _log(signed_in_client, base, ids["23CE001"], status="skipped")
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "Message pending parents" not in html
    assert "Showing 0 of 2 students" in signed_in_client.get(f"{base}?status=pending").get_data(
        as_text=True
    )


def test_page_asks_which_number_whatsapp_web_is_signed_in_to(signed_in_client, setup):
    base, _ = setup
    html = signed_in_client.get(base).get_data(as_text=True)
    assert '<dialog id="sending-as"' in html
    assert '<strong class="numeric">+91 90000 00001</strong>' in html
    assert 'href="https://web.whatsapp.com/" target="parent-notifier-whatsapp"' in html


def test_page_starts_with_the_pacing_state(signed_in_client, setup):
    base, _ = setup
    html = signed_in_client.get(base).get_data(as_text=True)
    assert 'data-wait-seconds="0" data-wait-reason=""' in html
    assert 'data-sent-today="0" data-daily-limit="60"' in html


def test_send_reports_the_gap_and_the_daily_limit_is_enforced(app, signed_in_client, setup, mentor):
    base, ids = setup
    data = _log(signed_in_client, base, ids["23CE001"]).get_json()
    assert data["pacing"]["reason"] == "gap"
    assert 0 < data["pacing"]["waitSeconds"] <= 20
    assert data["pacing"]["sentToday"] == 1
    with app.app_context():
        db.session.get(type(mentor), mentor.id).daily_send_limit = 1
        db.session.commit()
    response = _log(signed_in_client, base, ids["23CE001"])
    assert response.status_code == 409
    body = response.get_json()
    assert "today's limit of 1 messages" in body["error"]
    assert body["pacing"]["reason"] == "daily"
    assert len(_entries(app)) == 1
    assert _log(signed_in_client, base, ids["23CE001"], status="skipped").status_code == 200


def test_a_send_inside_the_gap_is_logged_as_a_warning(app, signed_in_client, setup, caplog):
    base, ids = setup
    _log(signed_in_client, base, ids["23CE001"])
    with caplog.at_level("WARNING"):
        assert _log(signed_in_client, base, ids["23CE001"]).status_code == 200
    assert "inside the gap wait" in caplog.text
