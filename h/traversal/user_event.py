from dataclasses import dataclass

from h.models_redis import UserEvent, get_user_event


@dataclass
class UserEventContext:
    """Context for annotation-based views."""

    user_event: UserEvent

    @property
    def image(self):
        return self.user_event["image"]


class UserEventRoot:
    """Root factory for routes whose context is an `UserEventRoot`."""

    def __init__(self, request):
        self.request = request

    def __getitem__(self, id):
        id = id.split(".")[0]
        user_event = get_user_event(id)
        if user_event is None:
            raise KeyError()

        return UserEventContext(user_event)
