from dataclasses import dataclass

from h.models_redis import UserEventRecord, fetch_user_event_record_by_session_id


@dataclass
class UserEventRecordContext:
    """Context for annotation-based views."""

    user_event_record: UserEventRecord

    @property
    def pk(self):
        return self.user_event_record.pk

    @property
    def session_id(self):
        return self.user_event_record.session_id


class UserEventRecordRoot:
    """Root factory for routes whose context is an `UserEventRecordRoot`."""

    def __init__(self, request):
        self.userid = request.authenticated_userid

    def __getitem__(self, session_id):
        record = fetch_user_event_record_by_session_id(session_id, self.userid)
        if record is None:
            raise KeyError()

        return UserEventRecordContext(record)
