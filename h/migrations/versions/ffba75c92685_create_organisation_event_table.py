"""create organisation event table"""
import sqlalchemy as sa
from alembic import op

import h

revision = "ffba75c92685"
down_revision = "8b4b4fdef955"


def upgrade():
    op.create_table(
        "organisation_event",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
        sa.Column("pubid", sa.Text(), unique=True, nullable=False),
        sa.Column(
            "created", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "date", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("groupid", sa.UnicodeText, nullable=False),
        sa.ForeignKeyConstraint(
            ["groupid"],
            ["group.pubid"],
            name=op.f("fk__organisation_event__groupid__group"),
        ),
        sa.Column("event_name", sa.UnicodeText),
        sa.Column("text", sa.UnicodeText),
        sa.Column("text_rendered", sa.UnicodeText),
        sa.Column("campus", sa.UnicodeText(), nullable=False),
    )
    op.create_index(
        op.f("ix__organisation_event_created"),
        "organisation_event",
        ["created"],
        unique=False,
    )
    op.create_index(
        op.f("ix__organisation_event_updated"),
        "organisation_event",
        ["updated"],
        unique=False,
    )
    op.create_index(
        op.f("ix__organisation_event_date"),
        "organisation_event",
        ["date"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix__organisation_event_date"), table_name="organisation_event")
    op.drop_index(op.f("ix__organisation_event_updated"), table_name="organisation_event")
    op.drop_index(op.f("ix__organisation_event_created"), table_name="organisation_event")
    op.drop_table("organisation_event")
