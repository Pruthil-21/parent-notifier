"""Logging an activity from a page: who is signed in, and their address for sign-in and
security events. Pages call this after their change has been saved."""

from flask import request
from flask_login import current_user

from parent_notifier.services.shared import activity


def log(category: str, event: str, **fields) -> None:
    fields.setdefault("actor", current_user if current_user.is_authenticated else None)
    if category == "security":
        fields.setdefault("ip_address", request.remote_addr)
    activity.record(category, event, **fields)
