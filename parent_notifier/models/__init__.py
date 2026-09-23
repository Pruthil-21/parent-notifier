"""Database models, one module per domain.

Importing any model runs this file first, so every table is registered with SQLAlchemy
whichever model a caller needs; migrations and create_all() then always see all tables.
"""

from parent_notifier.models import academics, accounts  # noqa: F401
