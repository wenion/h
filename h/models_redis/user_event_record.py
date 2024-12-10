from redis_om import Field, JsonModel
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
    target_uri: Optional[str]
    start: Optional[int]
    backdate: Optional[int]
    completed: int = Field(index=True)
    userid: str = Field(index=True)
    groupid: str = Field(index=True)
    shared: int = Field(index=True)
