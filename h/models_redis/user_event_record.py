from redis_om import Field, JsonModel
from redis_om.model import NotFoundError
from typing import Optional


class UserEventRecord(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'UserEventRecord'
    startstamp: int = Field(index=True)
    endstamp: int = Field(index=True)
    session_id: str = Field(full_text_search=True, sortable=True)
    task_name: Optional[str] = Field(full_text_search=True, sortable=True)
    description: str = Field(full_text_search=True, sortable=True)
    target_uri: str = Field(full_text_search=True, sortable=True)
    start: int = Field(index=True)
    completed: int = Field(index=True)
    userid: str = Field(index=True)
    groupid: str = Field(index=True)
    shared: int = Field(index=True)
    # steps: List[UserEvent] = Field(sortable=True)


def get_user_event_record(pk):
    user_event_record = UserEventRecord.get(pk)
    user_event_record_dict = user_event_record.dict()
    return user_event_record_dict


def create_user_event_record(
        startstamp,
        endstamp,
        session_id,
        task_name,
        description,
        target_uri,
        start,
        completed,
        userid,
        groupid,
        shared):
    user_event_record = UserEventRecord(
        startstamp = startstamp,
        endstamp = endstamp,
        session_id = session_id,
        task_name = task_name,
        description = description,
        target_uri = target_uri,
        start = start,
        completed = completed,
        userid = userid,
        groupid = groupid,
        shared = shared,
    )
    user_event_record.save()
    return user_event_record


def update_user_event_record(pk, update, steps):
    try:
        user_event_record = UserEventRecord.get(pk)
    except NotFoundError:
        return None
    else:
        user_event_record.endstamp = update['endstamp']
        user_event_record.completed = update['completed']
        user_event_record.shared = update['shared']
        # steps
        user_event_record.save()
        return user_event_record


def delete_user_event_record(pk):
    try:
        UserEventRecord.delete(pk)
    except:
        return False
    else:
        return True


def start_user_event_record(startstamp, session_id, task_name, description, target_uri, start, userid, groupid):
    return create_user_event_record(
        startstamp,
        -1,
        session_id,
        task_name,
        description,
        target_uri,
        start,
        0,
        userid,
        groupid,
        0
    )


def finish_user_event_record(pk, endstamp):
    update = {'endstamp': endstamp, 'completed': 1, 'shared': 0}
    return update_user_event_record(pk, update, -1)


def fetch_user_event_record_by_session_id(session_id, userid):
    query = UserEventRecord.find(
        (UserEventRecord.session_id == session_id) &
        (UserEventRecord.userid == userid)
        )
    total = query.all()
    return total[0] if len(total) > 0 else None


def batch_user_event_record(userid):
    if userid:
        total = UserEventRecord.find(
            (UserEventRecord.userid == userid) |
            (UserEventRecord.shared == 1)
            ).all()
    else:
        total = UserEventRecord.find(UserEventRecord.shared == 1).all()
    return total if len(total) > 0 else []
