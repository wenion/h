from datetime import datetime, timezone
import math
import pytz
from redis_om import Migrator
from redis_om import Field, JsonModel, EmbeddedJsonModel
from urllib.parse import urlparse
from typing import Optional


class PushRecord(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'PushRecord'
    timestamp: int = Field(index=True, sortable=True)
    push_type: str = Field(full_text_search=True, sortable=True) # SF - Shareflow, AK - Additional Knowledge, OE - Organisational event
    push_to: str = Field(index=True) #user_id
    push_content: str = Field(full_text_search=True)
    url: str = Field(index=True, full_text_search=True)
    additional_info: str = Field(full_text_search=True, sortable=True)


def add_push_record(timestamp, push_type, push_to, push_content, url, additional_info):
    pr = PushRecord(timestamp=timestamp,
                    push_type=push_type,
                    push_to=push_to,
                    push_content=push_content,
                    url=url,
                    additional_info=additional_info)
    pr.save()
    return pr


def fetch_push_record(pk):
    query = PushRecord.find(PushRecord.pk == pk)
    result = query.all()
    return result[0] if len(result) > 0 else None


def delete_push_record(pk):
    try:
        PushRecord.delete(pk)
        return True
    except:
        return False


def has_three_push(url, user_id):
    """
    Checking whether the most recent three Shareflow Pushes for the user are for the same task page
    """
    query = PushRecord.find(PushRecord.push_to == user_id)
    result = query.copy(limit=3).sort_by("-timestamp").execute()
    if not result or len(result) == 0:
        return False
    count = 0
    for record in result:
        if record.url == url:
            count += 1
    if count == 3:
        return True
    return False


def same_as_previous(user_id, url, push_type, push_content, additional_info):
    query = PushRecord.find(PushRecord.push_to == user_id)
    result = query.copy(limit=1).sort_by("-timestamp").execute()
    if not result or len(result) == 0:
        return False
    if result.url == url and result.push_type == push_type and result.push_content == push_content and result.additional_info == additional_info:
        return True
    return False

