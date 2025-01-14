from redis_om import Field, JsonModel


class FileMeta(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'FileMeta'
    filename: str = Field(index=True, full_text_search=True)
    file_id: str = Field(index=True, full_text_search=True)
    create_stamp: int = Field(index=True)
    update_stamp: int = Field(index=True)
    file_type: str = Field(index=True, full_text_search=True)
    file_path: str = Field(index=True, full_text_search=True)
    link: str = Field(index=True, full_text_search=True)
    userid: str = Field(index=True)
    access_permissions: str = Field(index=True)
    url: str = Field(index=True)
    deleted: int = Field(index=True)
