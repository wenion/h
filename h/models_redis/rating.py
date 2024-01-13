from datetime import datetime
from redis_om import Field, JsonModel
from redis_om.model import NotFoundError
from typing import Optional


class Rating(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'Rating'
    created: Optional[datetime] = Field(index=True)
    updated: Optional[datetime] = Field(index=True)
    created_timestamp: Optional[int] = Field(index=True)
    updated_timestamp: Optional[int] = Field(index=True)
    relevance: str = Field(index=True)
    timeliness: str = Field(index=True)
    url: Optional[str] = Field(index=True)
    base_url: Optional[str] = Field(index=True)
    userid: str = Field(index=True)

    def is_valid(id):
        try:
            rating = Rating.get(id)
        except NotFoundError as e:
            return None
        else:
            return rating

    def create(created, updated, relevance, timeliness, url, userid):
        rating = Rating(
            created = created,
            updated = updated,
            relevance = relevance,
            timeliness = timeliness,
            url = url,
            userid = userid,
        )
        rating.save()
        return rating

    def update(id, created, updated, relevance, timeliness, url, userid):
        rating = Rating.get(id)
        rating.created = created
        rating.updated = updated
        rating.relevance = relevance
        rating.timeliness = timeliness
        rating.url = url
        rating.userid = userid
        rating.save()
        return rating
    
    def delete(id):
        Rating.delete(id)

    def get_by_url(userid, url):
        return Rating.find(
            (Rating.userid == userid) &
            ((Rating.url == url) |
            (Rating.base_url == url))
        ).all()
        


