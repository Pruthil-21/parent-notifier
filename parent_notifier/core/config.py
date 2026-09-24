"""Settings for each environment, read from environment variables when the app starts."""

import os
import secrets
from datetime import timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

ENVIRONMENTS = ("development", "testing", "production")
TRUE_VALUES = {"1", "true", "yes", "on"}
TESTING_SECRET_KEY = "testing-only-secret-key"  # noqa: S105 (never used outside tests)


def load_config(env: str, instance_path: Path) -> dict[str, object]:
    if env not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment {env!r}; use one of {', '.join(ENVIRONMENTS)}.")
    database_url = _database_url(env, instance_path)
    # Vercel sets VERCEL=1. There the app is always behind its https proxy, and requests
    # over 4.5 MB are refused before they reach the app.
    on_vercel = _flag("VERCEL")
    return {
        "ENV_NAME": env,
        "TESTING": env == "testing",
        # Edited templates show on the next request in development, without a restart.
        "TEMPLATES_AUTO_RELOAD": env == "development",
        "SECRET_KEY": _secret_key(env, instance_path),
        "SQLALCHEMY_DATABASE_URI": database_url,
        "SQLALCHEMY_ENGINE_OPTIONS": _engine_options(database_url),
        # Behind a proxy such as Vercel's, trust its X-Forwarded headers for the client's
        # address (used by the sign-in lockout) and for https.
        "TRUST_PROXY": _flag("TRUST_PROXY", default=on_vercel),
        "APP_TIMEZONE": os.environ.get("APP_TIMEZONE", "Asia/Kolkata"),
        "MAX_CONTENT_LENGTH": _int("MAX_UPLOAD_MB", 4 if on_vercel else 5) * 1024 * 1024,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": _flag("SESSION_COOKIE_SECURE", default=on_vercel),
        "REMEMBER_COOKIE_DURATION": timedelta(days=30),
        "REMEMBER_COOKIE_HTTPONLY": True,
        "REMEMBER_COOKIE_SAMESITE": "Lax",
        "REMEMBER_COOKIE_SECURE": _flag("SESSION_COOKIE_SECURE", default=on_vercel),
        # Tests post forms without tokens; one test switches CSRF back on to prove it works.
        "WTF_CSRF_ENABLED": env != "testing",
        # Tokens last as long as the session, so a sign-in page left open all day still works.
        "WTF_CSRF_TIME_LIMIT": None,
        # One Waitress process serves the college, so counters can live in its memory.
        "RATELIMIT_STORAGE_URI": os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
        "RATELIMIT_STRATEGY": "moving-window",
        "COLLEGE_NAME": os.environ.get(
            "COLLEGE_NAME", "G. H. Patel College of Engineering & Technology"
        ),
        "COLLEGE_SHORT_NAME": os.environ.get("COLLEGE_SHORT_NAME", "GCET"),
        # The name as the Gujarati message signs it.
        "COLLEGE_NAME_GU": os.environ.get(
            "COLLEGE_NAME_GU", "જી. એચ. પટેલ કોલેજ ઓફ એન્જિનિયરિંગ એન્ડ ટેકનોલોજી"
        ),
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


def _database_url(env: str, instance_path: Path) -> str:
    """DATABASE_URL wins; otherwise tests get a private in-memory database and the other
    environments a SQLite file in the instance folder."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return _with_driver(url)
    if env == "testing":
        return "sqlite://"
    return f"sqlite:///{(instance_path / 'parent_notifier.db').as_posix()}"


def _with_driver(url: str) -> str:
    """Hosts such as Supabase give postgres:// or postgresql:// addresses; SQLAlchemy
    needs the driver named, and this app uses psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def _engine_options(url: str) -> dict[str, object]:
    """Postgres on a serverless host: a small pool per instance, connections checked
    before use, no prepared statements (transaction-mode poolers such as Supabase's
    don't support them), and encryption to any database that isn't on this machine."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql":
        return {}
    connect_args: dict[str, object] = {"prepare_threshold": None}
    if parsed.host not in {None, "localhost", "127.0.0.1"} and "sslmode" not in parsed.query:
        connect_args["sslmode"] = "require"
    return {
        "pool_size": 1,
        "max_overflow": 2,
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "connect_args": connect_args,
    }


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in TRUE_VALUES


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a whole number, got {raw!r}.") from None
