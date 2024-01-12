from dataclasses import dataclass

from h.models import OrganisationEvent


@dataclass
class OrganisationEventContext:
    """Context for organisation_event-based views."""

    organisation_event: OrganisationEvent = None


class OrganisationEventRoot:
    """Root factory for routes which deal with organisation events."""

    def __init__(self, request):
        self.request = request

    def __getitem__(self, pubid):
        organisation_event = self.request.find_service(name="organisation_event").get_by_public_id(
            pubid
        )

        if organisation_event is None:
            raise KeyError()

        return OrganisationEventContext(organisation_event=organisation_event)
