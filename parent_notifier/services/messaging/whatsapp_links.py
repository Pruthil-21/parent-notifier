"""The WhatsApp Web link that opens a chat with the message already typed."""

from urllib.parse import quote

BASE = "https://web.whatsapp.com/send"


def whatsapp_link(phone_e164: str, text: str) -> str:
    """web.whatsapp.com skips the "Continue to chat" page that wa.me shows on desktop,
    saving the mentor a click per parent. The text is fully percent-encoded."""
    digits = phone_e164.lstrip("+")
    if not digits.isdigit():
        raise ValueError("The phone number must be in +91XXXXXXXXXX form.")
    return f"{BASE}?phone={digits}&text={quote(text, safe='')}"
