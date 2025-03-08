import datetime

import sqlalchemy as sa

from h.db import Base
from h.models.group import Group


class ShareflowMetadata(Base):
    __tablename__ = "shareflow_metadata"

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

    shareflows = sa.orm.relationship(
        "Shareflow", back_populates="metadata_ref", cascade="all, delete-orphan")

    created = sa.Column(
        sa.DateTime,
        default=datetime.datetime.utcnow,
        server_default=sa.func.now(),  # pylint:disable=not-callable
        nullable=False,
        index=True,
    )

    updated = sa.Column(
        sa.DateTime,
        server_default=sa.func.now(),  # pylint:disable=not-callable
        default=datetime.datetime.utcnow,
        nullable=False,
        index=True,
    )

    deleted = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.sql.expression.false(),
    )

    startstamp = sa.Column(sa.DateTime, nullable=True)
    endstamp = sa.Column(sa.DateTime, nullable=True)

    session_id = sa.Column(sa.UnicodeText(), nullable=False, unique=True)
    task_name = sa.Column(sa.UnicodeText(), nullable=False, unique=True)
    description = sa.Column(sa.UnicodeText(), nullable=False, unique=True)

    backdate = sa.Column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    )
    pk = sa.Column(sa.UnicodeText())
    version = sa.Column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1"),
    )

    shared = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.sql.expression.false(),
    )

    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = sa.orm.relationship("User")

    groupid = sa.Column(
        sa.UnicodeText,
        default="__world__",
        server_default="__world__",
        nullable=False,
        index=True,
    )

    group = sa.orm.relationship(
        Group,
        primaryjoin=(Group.pubid == groupid),
        foreign_keys=[groupid],
        lazy="select",
    )
