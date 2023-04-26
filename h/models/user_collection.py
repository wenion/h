import datetime
import sqlalchemy as sa

from h.db import Base, types

class UserCollection(Base):
    __tablename__ = "user_collection"
    __table_args__ = (sa.UniqueConstraint("document_id", "user_id"),)

    #: The collection record id.
    id = sa.Column(types.URLSafeUUID, server_default=sa.func.uuid_generate_v1mc(), primary_key=True)
    
    #: The user who collect the document.
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )

    #: The document which has been collected.
    document_id = sa.Column(
        types.URLSafeUUID, 
        sa.ForeignKey("document_library.id"), 
        nullable=False,
        index=True,
    )

    #: The timestamp when the collection was created.
    created = sa.Column(
        sa.DateTime,
        default=datetime.datetime.utcnow,
        server_default=sa.func.now(),
        nullable=False,
    )

    #: The timestamp when the admin edited the collection status last.
    updated = sa.Column(
        sa.DateTime,
        server_default=sa.func.now(),
        default=datetime.datetime.utcnow,
        nullable=False,
    )

    #: Has the collection been cancelled?
    cancelled = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.sql.expression.false(),
    )

    user = sa.orm.relationship("User")
    document = sa.orm.relationship("DocumentLibrary")
    
    def __repr__(self):
        return f"<UserCollection user_id={self.user_id} document_id={self.document_id}>"
