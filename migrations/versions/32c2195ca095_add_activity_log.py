"""Add the activity log, which can only be added to.

On Postgres a trigger refuses any edit, and any delete of an entry under a year old.
The one change allowed is the database clearing actor_id when an account is deleted;
the entry keeps the name and username copied into it. Row-level security is on, as for
every table.

Revision ID: 32c2195ca095
Revises: cd1c47b26ded
Create Date: 2026-09-24 23:05:00

"""

import sqlalchemy as sa
from alembic import op

revision = "32c2195ca095"
down_revision = "cd1c47b26ded"
branch_labels = None
depends_on = None

APPEND_ONLY = """
CREATE FUNCTION activity_log_append_only() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.actor_id IS NOT NULL AND NEW.actor_id IS NULL
           AND (to_jsonb(NEW) - 'actor_id') = (to_jsonb(OLD) - 'actor_id') THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'The activity log cannot be changed';
    END IF;
    IF OLD.created_at > (now() AT TIME ZONE 'utc') - interval '365 days' THEN
        RAISE EXCEPTION 'Activity log entries are kept for at least a year';
    END IF;
    RETURN OLD;
END
$$ LANGUAGE plpgsql
"""


def upgrade():
    op.create_table(
        "activity_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("category", sa.String(length=12), nullable=False),
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_name", sa.String(length=80), nullable=True),
        sa.Column("username", sa.String(length=30), nullable=True),
        sa.Column("department", sa.String(length=60), nullable=True),
        sa.Column("target_type", sa.String(length=20), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("target_label", sa.String(length=120), nullable=True),
        sa.Column("class_id", sa.Integer(), nullable=True),
        sa.Column("class_label", sa.String(length=40), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["mentors.id"],
            name=op.f("fk_activity_log_actor_id_mentors"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activity_log")),
    )
    with op.batch_alter_table("activity_log", schema=None) as batch_op:
        batch_op.create_index(
            "ix_activity_log_actor_id_created_at", ["actor_id", "created_at"], unique=False
        )
        batch_op.create_index(
            "ix_activity_log_category_created_at", ["category", "created_at"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_activity_log_created_at"), ["created_at"])
        batch_op.create_index(
            "ix_activity_log_username_created_at", ["username", "created_at"], unique=False
        )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(APPEND_ONLY)
        op.execute(
            "CREATE TRIGGER activity_log_append_only BEFORE UPDATE OR DELETE ON activity_log "
            "FOR EACH ROW EXECUTE FUNCTION activity_log_append_only()"
        )
        op.execute('ALTER TABLE "activity_log" ENABLE ROW LEVEL SECURITY')


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER activity_log_append_only ON activity_log")
        op.execute("DROP FUNCTION activity_log_append_only()")
    op.drop_table("activity_log")
