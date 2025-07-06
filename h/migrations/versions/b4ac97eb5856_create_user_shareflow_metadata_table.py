"""Create user_shareflow_metadata table"""
import sqlalchemy as sa
from alembic import op


revision = "b4ac97eb5856"
down_revision = "f3590c4e54d8"


def upgrade():
    op.create_table(
        "user_shareflow_metadata",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            primary_key=True,
            nullable=False
        ),

        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="cascade"),

        sa.Column("shareflow_metadata_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["shareflow_metadata_id"],
            ["shareflow_metadata.id"],
            ondelete="cascade"
        ),

        sa.Column("score", sa.Integer(), nullable=False),
    )
    op.create_index(
        op.f("ix__user_shareflow_metadata_user_id"),
        "user_shareflow_metadata",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix__user_shareflow_metadata_shareflow_metadata_id"),
        "user_shareflow_metadata",
        ["shareflow_metadata_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix__user_shareflow_metadata_shareflow_metadata_id", table_name="user_shareflow_metadata")
    op.drop_index("ix__user_shareflow_metadata_user_id", table_name="user_shareflow_metadata")
    op.drop_table("user_shareflow_metadata")
