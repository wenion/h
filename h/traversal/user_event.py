from dataclasses import dataclass

from h.models_redis import UserEvent


@dataclass
class UserEventContext:
    """Context for user_event views."""

    user_event: UserEvent

    @property
    def id(self):
        return self.user_event.pk

    @property
    def image(self):
        return self.user_event.image


class UserEventRoot:
    """Root factory for routes whose context is an `UserEventRoot`."""

    def __init__(self, request):
        self._trace_service = request.find_service(name="trace")

    def __getitem__(self, id):
        trace = self._trace_service.get_trace_by_id(id)
        if trace is None:
            raise KeyError()

        return UserEventContext(trace)


class UserEventImageRoot(UserEventRoot):
    """Root factory for routes whose context is an `UserEventRoot`."""

    def __getitem__(self, id):
        id = id.split(".")[0]
        user_event_context = super().__getitem__(id)
        if user_event_context is None:
            raise KeyError()

        return user_event_context
