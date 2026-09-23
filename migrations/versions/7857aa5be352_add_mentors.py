"""Add mentors.

Revision ID: 7857aa5be352
Revises:
Create Date: 2026-09-23 22:27:18

"""

import sqlalchemy as sa
from alembic import op

revision = "7857aa5be352"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mentors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=80), nullable=False),
        sa.Column("username", sa.String(length=30), nullable=False),
        sa.Column("whatsapp_number", sa.String(length=16), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("recovery_code_hash", sa.String(length=255), nullable=False),
        sa.Column("theme", sa.String(length=10), server_default="system", nullable=False),
        sa.Column("message_language", sa.String(length=2), server_default="en", nullable=False),
        sa.Column("send_gap_seconds", sa.Integer(), server_default="20", nullable=False),
        sa.Column("burst_size", sa.Integer(), server_default="15", nullable=False),
        sa.Column("burst_pause_minutes", sa.Integer(), server_default="5", nullable=False),
        sa.Column("daily_send_limit", sa.Integer(), server_default="60", nullable=False),
        sa.Column("session_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "message_language IN ('en', 'gu')", name=op.f("ck_mentors_message_language")
        ),
        sa.CheckConstraint("theme IN ('system', 'light', 'dark')", name=op.f("ck_mentors_theme")),
        sa.CheckConstraint(
            "username = lower(username)", name=op.f("ck_mentors_username_lowercase")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mentors")),
        sa.UniqueConstraint("username", name=op.f("uq_mentors_username")),
    )


def downgrade():
    op.drop_table("mentors")
