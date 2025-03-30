import datetime
from uuid import UUID

import sqlalchemy as sa

from h.db import Base, types


class Shareflow(Base):
    __tablename__ = "shareflow"

    id = sa.Column(
        types.URLSafeUUID, server_default=sa.func.uuid_generate_v1mc(), primary_key=True
    )
    """The value of annotation.id, named here pubid following the convention of group.pubid"""

    index = sa.Column(sa.Integer, nullable=True)

    metadata_id = sa.Column(sa.Integer, sa.ForeignKey("shareflow_metadata.id"), nullable=False)
    
    metadata_ref = sa.orm.relationship("ShareflowMetadata", back_populates="shareflows")

    client_x = sa.Column(sa.Float)
    client_y = sa.Column(sa.Float)
    type = sa.Column(sa.UnicodeText())
    title = sa.Column(sa.UnicodeText())
    description = sa.Column(sa.UnicodeText())
    tag_name = sa.Column(sa.UnicodeText())
    timestamp = sa.Column(sa.DateTime, nullable=False)
    width = sa.Column(sa.Integer)
    height = sa.Column(sa.Integer)
    url = sa.Column(sa.UnicodeText())
    pk = sa.Column(sa.UnicodeText())
    version = sa.Column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1"),
    )

    image_id = sa.Column(sa.Integer, sa.ForeignKey("shareflow_image.id", ondelete="SET NULL"), nullable=True)
    """Foreign key reference to Image table"""
    image = sa.orm.relationship("ShareflowImage", back_populates="shareflow")
    """Relationship to access the associated image"""

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

    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = sa.orm.relationship("User")

    @property
    def uuid(self):
        """
        Return the UUID representation of the annotation's ID.

        Annotation IDs are stored in the DB as a UUID but represented in the app
        and API in a different format. This property returns the UUID version.
        """
        return UUID(types.URLSafeUUID.url_safe_to_hex(self.id))
