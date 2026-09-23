"""Indian mobile numbers: stored as E.164 (+919876543210), shown as +91 98765 43210."""


def format_for_display(e164: str) -> str:
    """Group a stored +91 number the way people read it aloud; leave anything else as is."""
    if e164.startswith("+91") and len(e164) == 13 and e164[1:].isdigit():
        return f"+91 {e164[3:8]} {e164[8:]}"
    return e164
