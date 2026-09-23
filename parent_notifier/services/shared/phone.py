"""Indian mobile numbers: stored as E.164 (+919876543210), shown as +91 98765 43210."""

import re

# Spaces, hyphens, dots and brackets people type between digit groups.
_SEPARATORS = re.compile(r"[\s\-.()]")
_MOBILE = re.compile(r"[6-9]\d{9}")


def normalise_indian_mobile(raw: str) -> str | None:
    """Accept 98765 43210, 098765-43210, 91 9876543210 or +91 (98765) 43210; return
    +919876543210, or None when it is not a 10-digit Indian mobile number."""
    digits = _SEPARATORS.sub("", raw or "")
    if digits.startswith("+91"):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return f"+91{digits}" if _MOBILE.fullmatch(digits) else None


def format_for_display(e164: str) -> str:
    """Group a stored +91 number the way people read it aloud; leave anything else as is."""
    if e164.startswith("+91") and len(e164) == 13 and e164[1:].isdigit():
        return f"+91 {e164[3:8]} {e164[8:]}"
    return e164
