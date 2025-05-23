"""create group shareflow_metadata table"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


revision = "f3590c4e54d8"
down_revision = "84a46bbca6b4"

Base = declarative_base()
Session = sessionmaker()


class Group(Base):
    __tablename__ = "group"
    id = sa.Column(sa.Integer, primary_key=True)
    pubid = sa.Column(sa.Text())
    authority = sa.Column(sa.UnicodeText())
    name = sa.Column(sa.UnicodeText())


def upgrade():
    op.create_table(
        "group_shareflow_metadata",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            primary_key=True,
            nullable=False
        ),

        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["group.id"], ondelete="cascade"),

        sa.Column("shareflow_metadata_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["shareflow_metadata_id"],
            ["shareflow_metadata.id"],
            ondelete="cascade"
        ),
    )
    op.create_index(
        op.f("ix__group_shareflow_metadata_group_id"),
        "group_shareflow_metadata",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix__group_shareflow_metadata_shareflow_metadata_id"),
        "group_shareflow_metadata",
        ["shareflow_metadata_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix__group_shareflow_metadata_shareflow_metadata_id", table_name="group_shareflow_metadata")
    op.drop_index("ix__group_shareflow_metadata_group_id", table_name="group_shareflow_metadata")
    op.drop_table("group_shareflow_metadata")
