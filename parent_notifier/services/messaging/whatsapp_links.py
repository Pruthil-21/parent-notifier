"""Links that open a WhatsApp chat with the parent's message already typed.

On a laptop, web.whatsapp.com goes straight to the chat, where wa.me would first show
a "Continue to chat" page, so that saves a click per parent. On a phone, wa.me opens
the WhatsApp app instead. The text is fully percent-encoded in both.
"""

from urllib.parse import quote

WEB = "https://web.whatsapp.com/send"
APP = "https://wa.me"


def _digits(phone_e164: str) -> str:
    digits = phone_e164.lstrip("+")
    if not digits.isdigit():
        raise ValueError("The phone number must be in +91XXXXXXXXXX form.")
    return digits


def whatsapp_link(phone_e164: str, text: str) -> str:
    """WhatsApp Web, for laptops and desktops."""
    return f"{WEB}?phone={_digits(phone_e164)}&text={quote(text, safe='')}"


def whatsapp_app_link(phone_e164: str, text: str) -> str:
    """The WhatsApp app, for phones and tablets."""
    return f"{APP}/{_digits(phone_e164)}?text={quote(text, safe='')}"
