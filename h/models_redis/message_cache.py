import json

from redis_om import Field, JsonModel
from redis_om.model import NotFoundError
from typing import Optional


class MessageCache(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'MessageCache'
    type: str = Field(index=True)
    id: str = Field(index=True)
    title: str = Field(full_text_search=True, index=True)
    message: str = Field(full_text_search=True, index=True)
    date: str = Field(full_text_search=True, index=True)
    show_flag: int = Field(index=True)
    unread_flag: int = Field(index=True)
    need_save_flag: int = Field(index=True)
    extra: Optional[str] = Field(full_text_search=True, index=True)
    target_uri: str = Field(full_text_search=True, sortable=True)
    timestamp: int = Field(index=True)
    userid: str = Field(index=True)
    groupid: str = Field(index=True)


def get_message_cache(pk):
    message = MessageCache.get(pk)
    extra = []
    if message.extra:
        try:
            extra = json.loads(message.extra)
        except Exception as e:
            extra = []
    message_dict = message.dict()
    message_dict["extra"] = extra
    return message_dict

def create_message_cache(
        type,
        id,
        title,
        message,
        date,
        show_flag,
        unread_flag,
        need_save_flag,
        extra,
        target_uri,
        userid,
        timestamp,
        groupid):
    try:
        extra = json.dumps(extra)
    except Exception as e:
        extra = None
    message_cache = MessageCache(
        type = type,
        id = id,
        title = title,
        message = message,
        date =date,
        show_flag = show_flag,
        unread_flag = unread_flag,
        need_save_flag = need_save_flag,
        extra = extra,
        target_uri = target_uri,
        userid = userid,
        timestamp = timestamp,
        groupid = groupid,
    )
    message_cache.save()
    message_cache.expire(10*60)
    return message_cache

def fetch_message_cache_by_user_id(userid):
    result = MessageCache.find(
        MessageCache.userid == userid
    ).sort_by("-timestamp").all()
    # parse a JSON string (extra) and convert it into a dictionary
    for r in result:
        extra = []
        if r.extra:
            try:
                extra = json.loads(r.extra)
            except Exception as e:
                extra = []
        r.extra = extra
    return result
