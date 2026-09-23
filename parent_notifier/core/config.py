"""Settings for each environment, read from environment variables when the app starts."""

import os
import secrets
from pathlib import Path

ENVIRONMENTS = ("development", "testing", "production")
TRUE_VALUES = {"1", "true", "yes", "on"}
TESTING_SECRET_KEY = "testing-only-secret-key"  # noqa: S105 (never used outside tests)


def load_config(env: str, instance_path: Path) -> dict[str, object]:
    if env not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment {env!r}; use one of {', '.join(ENVIRONMENTS)}.")
    return {
        "ENV_NAME": env,
        "TESTING": env == "testing",
        "SECRET_KEY": _secret_key(env, instance_path),
        "APP_TIMEZONE": os.environ.get("APP_TIMEZONE", "Asia/Kolkata"),
        "MAX_CONTENT_LENGTH": _int("MAX_UPLOAD_MB", 5) * 1024 * 1024,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": _flag("SESSION_COOKIE_SECURE"),
        "COLLEGE_NAME": os.environ.get(
            "COLLEGE_NAME", "G. H. Patel College of Engineering & Technology"
        ),
        "COLLEGE_SHORT_NAME": os.environ.get("COLLEGE_SHORT_NAME", "GCET"),
    }


def _secret_key(env: str, instance_path: Path) -> str:
    """Production must set SECRET_KEY. Development keeps a generated key in the
    instance folder so sign-ins survive restarts."""
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    if env == "production":
        raise RuntimeError("SECRET_KEY must be set in production.")
    if env == "testing":
        return TESTING_SECRET_KEY
    key_file = instance_path / "secret_key"
    if not key_file.exists():
        instance_path.mkdir(parents=True, exist_ok=True)
        key_file.write_text(secrets.token_hex(32), encoding="utf-8")
    return key_file.read_text(encoding="utf-8").strip()


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUE_VALUES


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a whole number, got {raw!r}.") from None
