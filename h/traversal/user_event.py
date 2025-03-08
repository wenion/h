from dataclasses import dataclass

from h.models import Shareflow, ShareflowImage


@dataclass
class UserEventContext:
    """Context for user_event views."""

    shareflow: Shareflow = None


class UserEventRoot:
    """Root factory for routes whose context is an `UserEventRoot`."""

    def __init__(self, request):
        self._request = request
        self._shareflow_service = request.find_service(name="shareflow")

    def __getitem__(self, id):
        shareflow = self._shareflow_service.get_trace_by_id(id)

        if shareflow is None:
            raise KeyError()

        return UserEventContext(shareflow)


@dataclass
class ShareflowImageContext:
    """Context for user_event views."""

    image: ShareflowImage = None


class ShareflowImageRoot:
    def __init__(self, request):
        self._request = request
        self._shareflow_service = request.find_service(name="shareflow")

    def __getitem__(self, id):
        id = id.split(".")[0]
        image = self._shareflow_service.get_shareflow_image_by_id(id)
        if image is None:
            raise KeyError()

        return ShareflowImageContext(image)
