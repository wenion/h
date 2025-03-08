"""Create ShareFlow table"""
import sqlalchemy as sa
from alembic import op

from h.db import types

revision = "dbacf5b87669"
down_revision = "ae285313a767"


def upgrade():
    op.create_table(
        "shareflow_metadata",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
        sa.Column(
            "created", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "deleted", sa.Boolean, server_default=sa.sql.expression.false(), nullable=False
        ),
        sa.Column("startstamp", sa.DateTime(), nullable=True),
        sa.Column("endstamp", sa.DateTime(), nullable=True),
        sa.Column("session_id", sa.UnicodeText),
        sa.Column("task_name", sa.UnicodeText),
        sa.Column("description", sa.UnicodeText),
        sa.Column("backdate", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("pk", sa.UnicodeText),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),

        sa.Column(
            "shared",
            sa.Boolean,
            server_default=sa.sql.expression.false(),
            nullable=False,
        ),

        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="cascade"),

        sa.Column(
            "groupid", sa.UnicodeText(), server_default="__world__", nullable=False
        ),
    )
    op.create_table(
        "shareflow_image",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True, nullable=False),
        sa.Column("image_data", sa.LargeBinary, nullable=False),
        sa.Column("image_type", sa.String, nullable=False),
    )
    op.create_table(
        "shareflow",
        sa.Column(
            "id",
            types.URLSafeUUID,
            server_default=sa.func.uuid_generate_v1mc(),
            primary_key=True,
        ),
        sa.Column("metadata_id", sa.Integer, sa.ForeignKey("shareflow_metadata.id"), nullable=False, index=True),
        sa.Column(
            "created", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "deleted", sa.Boolean, server_default=sa.sql.expression.false(), nullable=False
        ),
        sa.Column("client_x", sa.Float, nullable=True),
        sa.Column("client_y", sa.Float, nullable=True),
        sa.Column("type", sa.UnicodeText),
        sa.Column("title", sa.UnicodeText),
        sa.Column("description", sa.UnicodeText),
        sa.Column("tag_name", sa.UnicodeText),
        sa.Column("timestamp", sa.DateTime, nullable=True),

        sa.Column("width", sa.UnicodeText),
        sa.Column("height", sa.UnicodeText),
        sa.Column("url", sa.UnicodeText),
        sa.Column("pk", sa.UnicodeText),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),

        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["image_id"], ["shareflow_image.id"], ondelete="SET NULL"),

        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="cascade"),
    )


def downgrade():
    op.drop_table("shareflow")
    op.drop_table("shareflow_image")
    op.drop_table("shareflow_metadata")
