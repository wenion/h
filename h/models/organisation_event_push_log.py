import datetime
import sqlalchemy as sa

from h.db import Base


class OrganisationEventPushLog(Base):
    """
    An auth ticket.

    An auth ticket represents an open authentication session for a logged-in
    user. The ``id`` is typically stored in an ``auth`` cookie, provided by
    :py:class:`pyramid_authsanity.sources.CookieAuthSource`.
    """

    __tablename__ = "organisation_event_push_log"

    #: The id that is typically stored in the cookie, it should be a
    #: cryptographically random string with an appropriate amount of entropy.
    id = sa.Column(sa.Integer(), autoincrement=True, primary_key=True)

    user_id = sa.Column(
        sa.Integer, sa.ForeignKey("user.id"), nullable=False
    )
    #: The user whose auth ticket it is
    user = sa.orm.relationship("User")
    
    created = sa.Column(
        sa.DateTime,
        default=datetime.datetime.utcnow,
        server_default=sa.func.now(),
        nullable=False,
    )

    organisation_event_id = sa.Column(
        sa.Integer, sa.ForeignKey("organisation_event.id", ondelete="cascade"), nullable=False
    )

    organisation_event = sa.orm.relationship("OrganisationEvent")

    dismissed = sa.Column(
        sa.Boolean, default=False, server_default=(sa.sql.expression.false())
    )
