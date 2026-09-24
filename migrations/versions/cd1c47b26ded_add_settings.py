"""Add college-wide settings, starting with who may create an account.

With no row, sign-up stays off, so only the admin can add accounts.

Revision ID: cd1c47b26ded
Revises: 2b079818aeae
Create Date: 2026-09-24 22:40:00

"""

import sqlalchemy as sa
from alembic import op

revision = "cd1c47b26ded"
down_revision = "2b079818aeae"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("value", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_settings")),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE "settings" ENABLE ROW LEVEL SECURITY')


def downgrade():
    op.drop_table("settings")
