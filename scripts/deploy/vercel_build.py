"""Vercel's build step: bring the database up to date.

The migrations run against DATABASE_URL, unless RUN_MIGRATIONS is "false" or the build
is a pull request preview, which shares the live database and must not change it before
the change is merged.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Run as a file, Python only sees this script's folder; the app lives at the root.
sys.path.insert(0, str(ROOT))


def migrate() -> None:
    if os.environ.get("RUN_MIGRATIONS", "").strip().lower() == "false":
        print("Skipped migrations: RUN_MIGRATIONS is false")
        return
    if os.environ.get("VERCEL_ENV") == "preview":
        print("Skipped migrations: preview builds leave the live database alone")
        return
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is not set; add it in the Vercel project settings.")
    from flask_migrate import upgrade

    from parent_notifier import create_app
    from parent_notifier.core.extensions import init_migrations

    app = create_app()
    init_migrations(app)  # a serverless app skips this at start
    with app.app_context():
        upgrade()
    print("Database is up to date")


if __name__ == "__main__":
    migrate()
