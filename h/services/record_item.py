from redis_om.model import NotFoundError
from pydantic.error_wrappers import ValidationError

from h.models_redis import UserEventRecord


class RecordItemService:
    """A service for manipulating record item (user event record)."""

    def __init__(self, request):
        """
        Create a new record item service.
        """
        self.request = request

    @staticmethod
    def get_record_item_by_id(session_id_or_id):
        try:
            item = UserEventRecord.get(session_id_or_id)
            return item
        except NotFoundError:
            user_event_records = UserEventRecord.find(
                UserEventRecord.pk == session_id_or_id
            ).all()
            if len(user_event_records):
                return user_event_records[0]
            else:
                return None

    @staticmethod
    def init_user_event_record(data):
        """Create an user event record."""
        user_event_record = UserEventRecord(**data)
        user_event_record.save()
        return user_event_record

    @staticmethod
    def finish_user_event_record(id, endstamp):
        """Update an user event record."""
        user_event_record = RecordItemService.get_record_item_by_id(id)
        user_event_record.endstamp = endstamp
        user_event_record.completed = 1
        user_event_record.save()
        return user_event_record

    @staticmethod
    def delete_user_event_record(id):
        """Delete an user event record."""
        try:
            UserEventRecord.delete(id)
        except:
            return False
        return True


def record_item_factory(_context, request):
    """Return a RecordItemService instance for the request."""
    return RecordItemService(request)
