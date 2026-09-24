"""Vercel's build step: publish the static files and bring the database up to date.

Vercel serves files in public/ straight from its CDN, so the app's CSS and JavaScript
are copied to public/static/, the same paths the pages link to. Then the database
migrations run against DATABASE_URL, unless RUN_MIGRATIONS is "false".
"""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Run as a file, Python only sees this script's folder; the app lives at the root.
sys.path.insert(0, str(ROOT))


def publish_static() -> None:
    target = ROOT / "public" / "static"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(ROOT / "parent_notifier" / "static", target)
    print(f"Copied static files to {target.relative_to(ROOT)}")


def migrate() -> None:
    if os.environ.get("RUN_MIGRATIONS", "").strip().lower() == "false":
        print("Skipped migrations: RUN_MIGRATIONS is false")
        return
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is not set; add it in the Vercel project settings.")
    from flask_migrate import upgrade

    from parent_notifier import create_app

    with create_app().app_context():
        upgrade()
    print("Database is up to date")


if __name__ == "__main__":
    publish_static()
    migrate()
