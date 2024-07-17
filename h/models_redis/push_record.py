from datetime import datetime, timezone
import math
import pytz
from redis_om import Migrator
from redis_om import Field, JsonModel, EmbeddedJsonModel
from urllib.parse import urlparse
from typing import Optional
import json


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


def stop_pushing(url, user_id):
    """
    Checking whether the most recent three Shareflow Pushes for the user are for the same task page, or if the previous push on this task page is greater than 0.9
    """
    try:
        query = PushRecord.find(PushRecord.push_to == user_id)
        result = query.copy(limit=3).sort_by("-timestamp").execute()
        if not result or len(result) == 0:
            return False
        count = 0
        for record in result:
            if record.url == url:
                additional_info = json.loads(record.additional_info)
                if additional_info:
                    for task in additional_info:
                        if task["certainty"] > 0.9:
                            return True
                count += 1
        if count == 3:
            return True
        return False
    except:
        return False


def same_as_previous(user_id, url, push_type, push_content, additional_info):
    try:
        query = PushRecord.find(PushRecord.push_to == user_id)
        result = query.copy(limit=1).sort_by("-timestamp").execute()
        if not result or len(result) != 1:
            return False
        result = result[0]
        if result.url == url and result.push_type == push_type and result.push_content == push_content and result.additional_info == additional_info:
            return True
        return False
    except:
        return False


def fetch_all_push_record():
    try:
        query = PushRecord.find()
        result = query.all()
        push_records = []
        for index, record in enumerate(result):
            push_records.append({"id": index,
                                "timestamp": record.timestamp,
                                "push_type": record.push_type,
                                "push_to": record.push_to,
                                "push_content": record.push_content,
                                "additional_info": record.additional_info,
                                "url": record.url})
        return push_records if len(push_records) > 0 else None
    except:
        return None

