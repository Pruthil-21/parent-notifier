"""Throttling for forms that check a password or recovery code.

Only failed attempts count. Limits apply per username, so one account cannot be guessed
at, and per IP address, so one computer cannot work through many usernames. Sign-in and
password reset share both counters: a lockout on one is a lockout on the other.
"""

import time
from collections.abc import Callable

from flask import g, request
from flask_limiter.util import get_remote_address
from flask_login import current_user

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


# Wrong current passwords on the profile page count against the same username counter,
# so a borrowed session cannot be used to guess the password either.
throttle_failed_password_checks = _limit(
    FAILURES_PER_USERNAME, "credentials-username", lambda: current_user.username
)


def record_failed_attempt() -> None:
    g.credentials_failed = True


def retry_wait() -> str:
    """How long until the breached limit lets the next request through, like "12 minutes"."""
    breached = limiter.current_limit
    seconds = breached.reset_at - time.time() if breached else WINDOW_MINUTES * 60
    # The limiter rounds its reset time up to the next second, so rounding up again
    # could promise 16 minutes for a 15-minute window.
    minutes = max(1, round(seconds / 60))
    return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"


def lockout_message(action: str) -> str:
    """For example "Too many sign-in attempts. Try again in 12 minutes." """
    return f"Too many {action} attempts. Try again in {retry_wait()}."
