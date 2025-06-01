import datetime

from redis_om import Field, JsonModel
from typing import Optional


class VersionControlMeta(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'VersionControlMeta'
    external_ref: str = Field(index=True)
    version: int = Field(index=True)
    current: str = Field(index=True)


class VersionControlNode(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'VersionControlNode'
    data: str = Field(index=True)
    external_ref: str = Field(index=True)
    version: int = Field(index=True)
    prev: Optional[str] = Field(index=True)
    created: datetime.datetime = (
        Field(default_factory=datetime.datetime.utcnow)
    )
