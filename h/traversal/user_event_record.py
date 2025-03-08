from dataclasses import dataclass

from h.models import ShareflowMetadata


@dataclass
class UserEventRecordContext:
    """Context for user event record-based views."""

    shareflow_metadata: ShareflowMetadata

    @property
    def id(self):
        return self.shareflow_metadata.session_id


class UserEventRecordRoot:
    """Root factory for routes whose context is an `UserEventRecordRoot`."""

    def __init__(self, request):
        self._recording_service = request.find_service(name="shareflow")

    def __getitem__(self, id):
        record = self._recording_service.read_shareflow_metadata_by_session_id(id)
        if record is None:
            raise KeyError()

        return UserEventRecordContext(record)
