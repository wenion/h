from h.models import OrganisationEventPushLog


class OrganisationEventPushLogService:
    """A service for manipulating organizations."""

    def __init__(self, session, user_service, organisation_event_service):
        """
        Create a new organizations service.

        :param session: the SQLAlchemy session object
        """
        self.session = session
        self._user_service = user_service
        self._organisation_event_service = organisation_event_service

    def create(self, userid, organisation_event_pubid):
        user = self._user_service.fetch(userid)
        if user is None:
            raise ValueError(f"Cannot find user with userid {userid}")

        organisation_event = self._organisation_event_service.get_by_pubid(organisation_event_pubid)
        if organisation_event is None:
            raise ValueError(f"Cannot find origanisation with pubid {organisation_event_pubid}")
        
        organization = OrganisationEventPushLog(user=user, organisation_event=organisation_event)
        self.session.add(organization)
        return organization
    
    def fetch_by_userid_and_pubid(self, userid, pubid):
        user = self._user_service.fetch(userid)
        if user is None:
            raise ValueError(f"Cannot find user with userid {userid}")
        
        organisation_event = self._organisation_event_service.get_by_pubid(pubid)
        if organisation_event is None:
            raise ValueError(f"Cannot find origanisation with pubid {pubid}")

        query_result = self.session.query(OrganisationEventPushLog) \
        .filter(OrganisationEventPushLog.user_id==user.id) \
        .filter(OrganisationEventPushLog.organisation_event_id==organisation_event.id) \
        .one_or_none()
        # .filter(OrganisationEventPushLog.dismissed==dismissed) \
        return query_result


def factory(_context, request):
    return OrganisationEventPushLogService(
        request.db,
        user_service=request.find_service(name="user"),
        organisation_event_service=request.find_service(name="organisation_event"),
    )