from redis_om.model import NotFoundError

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
        except NotFoundError:
            user_event_records = UserEventRecord.find(
                UserEventRecord.session_id == session_id_or_id
            ).all()
            if len(user_event_records):
                item = user_event_records[0]
            else:
                return None
        finally:
            return item

    @staticmethod
    def basic_record_item(item):
        return {
            'id': item.pk,
            'sessionId': item.session_id,
            'taskName': item.task_name,
            'description': item.description,
            'groupid': item.groupid,
            'role': 'unknown',
            'shared': True if item.shared else False,
            'timestamp': item.startstamp,
            'userid': item.userid,
        }

    @staticmethod
    def record_item_search_query(userid, shared):
        shared_int = 1 if shared else 0
        user_event_records = UserEventRecord.find(
            (UserEventRecord.userid == userid) |
            (UserEventRecord.shared == shared_int)
            ).all()
        
        all = []
        for item in user_event_records:
            all.append(RecordItemService.basic_record_item(item))
        return all

    @staticmethod
    def init_user_event_record(data):
        """Create an user event record."""
        user_event_record = UserEventRecord(**data)
        user_event_record.save()
        return RecordItemService.basic_record_item(user_event_record)

    @staticmethod
    def finish_user_event_record(id, endstamp):
        """Update an user event record."""
        user_event_record = UserEventRecord.get(id)
        user_event_record.endstamp = endstamp
        user_event_record.completed = 1
        user_event_record.save()
        return RecordItemService.basic_record_item(user_event_record)

    @staticmethod
    def share_user_event_record(id, shared):
        """Update an user event record."""
        user_event_record = UserEventRecord.get(id)
        user_event_record.shared = shared
        user_event_record.save()
        return RecordItemService.basic_record_item(user_event_record)

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
