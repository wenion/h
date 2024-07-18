import time

from redis_om import Field, JsonModel
from redis_om.model import NotFoundError


class DataComic(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'DataComic'
    createdstamp: int = Field(index=True)
    updatedstamp: int = Field(index=True)
    session_id: str = Field(full_text_search=True, sortable=True)
    userid: str = Field(index=True)
    content: str = Field(full_text_search=True, sortable=True)


def get_comic(pk):
    comic = DataComic.get(pk)
    comic_dict = comic.dict()
    return comic_dict


def create_comic(session_id, userid, content):
    comic = DataComic(
        createdstamp = int(time.time()),
        updatedstamp = 0,
        session_id = session_id,
        userid = userid,
        content = content
    )
    comic.save()
    return comic


def update_comic(pk, content):
    try:
        comic = DataComic.get(pk)
    except NotFoundError:
        return None
    else:
        comic.updatedstamp = int(time.time()),
        comic.content = content
        comic.save()
        return comic


def delete_comic(pk):
    try:
        DataComic.delete(pk)
    except:
        return False
    else:
        return True


def fetch_comic(session_id, userid):
    query = DataComic.find(
        (DataComic.session_id == session_id) & 
        (DataComic.userid == userid))
    
    total = query.all()
    return total[0] if len(total) > 0 else None