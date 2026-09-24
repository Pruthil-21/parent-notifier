"""Send one English and Gujarati message; drop the language choice.

Every parent now gets the same message, each part in English then Gujarati, so the
mentor's default language and the language kept with each send go.

Revision ID: c6f2a8e41d73
Revises: b3e7d51c9a02
Create Date: 2026-09-25 14:00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "c6f2a8e41d73"
down_revision = "b3e7d51c9a02"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("mentors", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_mentors_message_language"), type_="check")
        batch_op.drop_column("message_language")
    with op.batch_alter_table("send_log", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_send_log_language"), type_="check")
        batch_op.drop_column("language")


def downgrade():
    with op.batch_alter_table("send_log", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("language", sa.String(length=2), server_default="en", nullable=False)
        )
        batch_op.create_check_constraint("language", "language IN ('en', 'gu')")
    with op.batch_alter_table("mentors", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("message_language", sa.String(length=2), server_default="en", nullable=False)
        )
        batch_op.create_check_constraint("message_language", "message_language IN ('en', 'gu')")
