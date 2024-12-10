from dataclasses import dataclass

from h.models_redis import UserEventRecord


@dataclass
class UserEventRecordContext:
    """Context for user event record-based views."""

    user_event_record: UserEventRecord

    @property
    def id(self):
        return self.user_event_record.pk


class UserEventRecordRoot:
    """Root factory for routes whose context is an `UserEventRecordRoot`."""

    def __init__(self, request):
        self._recording_service = request.find_service(name="record_item")

    def __getitem__(self, id):
        record = self._recording_service.get_record_item_by_id(id)
        if record is None:
            raise KeyError()

        return UserEventRecordContext(record)
