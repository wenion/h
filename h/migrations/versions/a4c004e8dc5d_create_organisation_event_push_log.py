"""create organisation event push log"""
from alembic import op
import sqlalchemy as sa


revision = "a4c004e8dc5d"
down_revision = "ffba75c92685"


def upgrade():
    op.create_table(
        "organisation_event_push_log",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("fk__organisation_event_push_log__userid__user"),
        ),
        sa.Column(
            "created", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("organisation_event_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organisation_event_id"],
            ["organisation_event.id"],
            name=op.f("fk__organisation_event_push_log__organisation_event_id__organisation_event"),
        ),
        sa.Column("dismissed", sa.Boolean(), server_default=sa.sql.expression.false(),)
    )
    op.create_index(
        op.f("ix__organisation_event_push_log_created"),
        "organisation_event_push_log",
        ["created"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix__organisation_event_push_log_created"), table_name="organisation_event_push_log")
    op.drop_table("organisation_event_push_log")
