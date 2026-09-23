"""Throttling for forms that check a password or recovery code.

Only failed attempts count. Limits apply per username, so one account cannot be guessed
at, and per IP address, so one computer cannot work through many usernames. Sign-in and
password reset share both counters: a lockout on one is a lockout on the other.
"""

import math
import time
from collections.abc import Callable

from flask import g, request
from flask_limiter.util import get_remote_address

from parent_notifier.core.extensions import limiter
from parent_notifier.services.accounts.credentials import normalise_username

WINDOW_MINUTES = 15
FAILURES_PER_USERNAME = 5
FAILURES_PER_ADDRESS = 20


def _submitted_username() -> str:
    return normalise_username(request.form.get("username", ""))


def _attempt_failed(_response) -> bool:
    return g.get("credentials_failed", False)


def _limit(count: int, scope: str, key_func: Callable[[], str]):
    return limiter.shared_limit(
        f"{count} per {WINDOW_MINUTES} minutes",
        scope=scope,
        key_func=key_func,
        methods=["POST"],
        deduct_when=_attempt_failed,
    )


_by_username = _limit(FAILURES_PER_USERNAME, "credentials-username", _submitted_username)
_by_address = _limit(FAILURES_PER_ADDRESS, "credentials-address", get_remote_address)


def throttle_failed_attempts(view):
    return _by_username(_by_address(view))


def record_failed_attempt() -> None:
    g.credentials_failed = True


def lockout_message(action: str) -> str:
    """For example "Too many sign-in attempts. Try again in 12 minutes." """
    breached = limiter.current_limit
    seconds = breached.reset_at - time.time() if breached else WINDOW_MINUTES * 60
    minutes = max(1, math.ceil(seconds / 60))
    unit = "minute" if minutes == 1 else "minutes"
    return f"Too many {action} attempts. Try again in {minutes} {unit}."
