"""Add extra data to shareflow_metadata"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.mutable import MutableDict


revision = "84a46bbca6b4"
down_revision = "df3471a91cd2"


def upgrade():
    op.add_column(
        "shareflow_metadata",
        sa.Column(
            "extra",
            MutableDict.as_mutable(pg.JSONB),
            server_default=sa.func.jsonb("{}"),
            nullable=False,
        )
    )

    op.execute("UPDATE \"shareflow_metadata\" SET extra = '{}'")


def downgrade():
    op.drop_column("shareflow_metadata", "extra")
