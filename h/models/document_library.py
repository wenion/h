import datetime
import sqlalchemy as sa

from h.db import Base, types

class DocumentLibrary(Base):
    __tablename__ = "document_library"
    __table_args__ = (sa.UniqueConstraint("digest"), sa.UniqueConstraint("web_uri"))
    
    #: The document id
    id = sa.Column(types.URLSafeUUID, server_default=sa.func.uuid_generate_v1mc(), primary_key=True)
    
    #: The denormalized value of the first DocumentMeta record with type title.
    title = sa.Column("title", sa.UnicodeText())
    
    #: The denormalized value of the "best" http(s) DocumentURI for this Document.
    web_uri = sa.Column("web_uri", sa.UnicodeText(), nullable=True)

    #: The digest value of document using sha-256/sha-512
    digest = sa.Column("digest", sa.String(128), nullable=True)

    #: The visibility of document, could be public, private ...
    visibility = sa.Column("visibility", sa.String(64))
    
    #: The timestamp when the document was created.
    created = sa.Column(
        sa.DateTime,
        default=datetime.datetime.utcnow,
        server_default=sa.func.now(),
        nullable=False,
    )
    
    #: The timestamp when the admin edited the document last.
    updated = sa.Column(
        sa.DateTime,
        server_default=sa.func.now(),
        default=datetime.datetime.utcnow,
        nullable=False,
    )
    
    #: The original document_id in table document
    external_id = sa.Column(sa.Integer, nullable=True, default=None)
    
    def __repr__(self):
        return f"<Document {self.id}>"
