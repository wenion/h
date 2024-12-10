from datetime import datetime
from redis_om import Field, JsonModel
from typing import Optional


class UserEvent(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'UserEvent'
    event_type: str = Field(index=True, full_text_search=True)
    timestamp: int = Field(index=True)
    tag_name: str = Field(index=True)
    text_content: str = Field(index=True)
    base_url: str = Field(index=True)
    userid: str = Field(index=True)
    ip_address: Optional[str] = Field(full_text_search=True, sortable=True)
    interaction_context: Optional[str] = Field(full_text_search=True, sortable=True)
    event_source: Optional[str] = Field(full_text_search=True, sortable=True)
    system_time: Optional[datetime]
    x_path: Optional[str] = Field(full_text_search=True, sortable=True)
    offset_x: Optional[float] = Field(full_text_search=True, sortable=True)
    offset_y: Optional[float] = Field(full_text_search=True, sortable=True)
    doc_id: Optional[str] = Field(full_text_search=True, sortable=True)
    region: Optional[str] = Field(index=True, default="Australia/Sydney")
    session_id: Optional[str] = Field(full_text_search=True, sortable=True)
    task_name: Optional[str] = Field(full_text_search=True, sortable=True)
    width: Optional[int] = Field(full_text_search=True, sortable=True)
    height: Optional[int] = Field(full_text_search=True, sortable=True)
    image: Optional[str]
    title: Optional[str] = Field(full_text_search=True, sortable=True)
    label: Optional[str] = Field(full_text_search=True, sortable=True)
    action_type: Optional[str] = Field(full_text_search=True, sortable=True)
