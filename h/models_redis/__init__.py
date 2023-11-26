from datetime import datetime, timezone
import math
import pytz
import openai
import logging

from redis_om import Migrator
from redis_om import Field, JsonModel, EmbeddedJsonModel
from pydantic import NonNegativeInt
from typing import Optional

log = logging.getLogger(__name__)

class UserRole(EmbeddedJsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'UserRole'
    userid: str = Field(index=True)
    faculty: str = Field(index=True)
    teaching_role: str = Field(index=True)
    teaching_unit: str = Field(index=True)
    joined_year: NonNegativeInt = Field(index=True)
    years_of_experience: NonNegativeInt = Field(index=True)
    expert: NonNegativeInt = Field(index=True)


class Result(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'Result'
    title: str = Field(index=True)
    url: str = Field(index=True)
    summary: Optional[str] #= Field(index=True, full_text_search=True, default="")
    highlights: Optional[str] #= Field(index=True, full_text_search=True, default="")


class Bookmark(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'Bookmark'
    query: str = Field(index=True, full_text_search=True)
    user: UserRole                      # UserRole pk
    result: str = Field(index=True)     # Result pk
    deleted: int = Field(index=True, default=0)


class UserEvent(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'UserEvent'
    event_type: str = Field(index=True, full_text_search=True)
    timestamp: int = Field(index=True)
    tag_name: str = Field(index=True)     # Result pk
    text_content: str = Field(index=True)
    base_url: str = Field(index=True)
    userid: str = Field(index=True)
    ip_address: Optional[str]
    interaction_context: Optional[str]
    event_source: Optional[str] # Navigate Mouse Page Keyboard
    system_time: Optional[datetime]
    x_path: Optional[str]
    doc_id: Optional[str]
    region: Optional[str] = Field(index=True, default="Australia/Sydney")


def add_user_event(
        userid,
        event_type,
        timestamp,
        tag_name,
        text_content,
        base_url,
        ip_address,
        interaction_context,
        event_source,
        x_path,
        doc_id,
        region
        ):
    user_event = UserEvent(
        userid=userid,
        event_type=event_type,
        timestamp=timestamp,
        tag_name=tag_name,
        text_content=text_content,
        base_url=base_url,
        ip_address=ip_address,
        interaction_context=interaction_context,
        event_source=event_source,
        x_path=x_path,
        doc_id=doc_id,
        system_time=datetime.now().replace(tzinfo=timezone.utc).astimezone(tz=None),
        region=region,
    )
    user_event.save()
    return user_event


def get_user_event(pk):
    user_event = UserEvent.get(pk)
    return {
        'pk': user_event.pk,
        'userid': user_event.userid,
        'event_type': user_event.event_type,
        'timestamp': user_event.timestamp,
        'tag_name': user_event.tag_name,
        'text_content': user_event.text_content,
        'base_url': user_event.base_url,
        'ip_address': user_event.ip_address,
        'interaction_context': user_event.interaction_context,
        'event_source': user_event.event_source,
        'x_path': user_event.x_path,
        'doc_id': user_event.doc_id,
        'system_time': user_event.system_time.astimezone(pytz.timezone("Australia/Sydney")).isoformat() if user_event.system_time else None,
        'region': user_event.region,
    }


class Rating(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'Rating'
    created_timestamp: int = Field(index=True)
    updated_timestamp: int = Field(index=True)
    relevance: str = Field(index=True)
    timeliness: str = Field(index=True)
    base_url: str = Field(index=True)
    userid: str = Field(index=True)


def fetch_user_event(userid, offset, limit, sortby):
    query = UserEvent.find(
        UserEvent.userid == userid
        )
    total = len(query.all())
    # if offset > math.ceil(total / limit):
    #     offset = math.ceil(total / limit)

    results = query.copy(offset=offset, limit=limit).sort_by(sortby).execute(exhaust_results=False)

    table_result=[]
    for item in results:
        json_item = get_user_event(item.pk)
        table_result.append(json_item)
    return {
        "table_result": table_result,
        "total": total,
        "offset": offset,
        "limit": limit,
        }


def get_user_event_fields():
    return UserEvent.schema()["properties"]


class UserFile(JsonModel):  # repository file's attribute
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'UserFile'
    userid: str = Field(index=True)
    name: str = Field(index=True)
    path: str = Field(index=True)
    directory_path: str = Field(index=True)
    filetype: str = Field(index=True)
    link: str = Field(index=True)
    depth: NonNegativeInt = Field(index=True)
    accessibility: str = Field(index=True)
    ingested: int = Field(index=True, default=0)
    source: str = Field(index=True)
    deleted: int = Field(index=True, default=0)


__all__ = (
    "UserRole",
    "Result",
    "Bookmark",
    "UserEvent",
    "Rating",
    "UserFile",
)


def add_user_role(userid, faculty, role, unit, year, experience, expert):
    user_role = UserRole.find(
        UserRole.userid == userid
        ).all()
    if len(user_role):
        return user_role[0]
    else:
        user_role = UserRole(
            userid=userid,
            faculty=faculty,
            teaching_role=role,
            teaching_unit=unit,
            joined_year=year,
            years_of_experience=experience,
            expert=expert
        )
        user_role.save()
        return user_role


def update_user_role(userid, faculty, role, unit, year, experience, expert):
    user_roles = UserRole.find(
        UserRole.userid == userid
        ).all()
    if len(user_roles):
        user_role = user_roles[0]
        user_role.faculty = faculty
        user_role.teaching_role = role
        user_role.teaching_unit = unit
        user_role.joined_year = year
        user_role.years_of_experience = experience
        if expert:
            user_role.expert = expert
        user_role.save()
        return True
    else:
        return False


def get_user_role_by_userid(userid):
    return add_user_role(userid, "", "", "", 0, 0, 0)


def get_user_role(request):
    """
    Return the user for the request or None.

    :rtype: h.models.User or None

    """
    if request.authenticated_userid is None:
        return None
    user_role = get_user_role_by_userid(request.authenticated_userid)

    return user_role


def check_redis_keys(username, authority):
    userid = f"acct:{username}@{authority}"
    user_role = UserRole.find(
        UserRole.userid == userid
    ).all()

    if not len(user_role):
        user_role_kwargs = {
            "userid": userid,
            "faculty": "",
            "teaching_role": "",
            "teaching_unit": "",
            "joined_year": 0,
            "years_of_experience": 0,
            "expert": 0,
        }
        user_role = UserRole(**user_role_kwargs)
        # user_role.save()


def attach_sql(config):
    engine = config.registry["sqlalchemy.engine"]
    try:
        result = engine.execute('SELECT username, authority FROM public."user";')
    except Exception as e:
        log.exception("unable to attach sql")
    else:
        rows = result.fetchall()
        for row in rows:
            check_redis_keys(row[0], row[1])
        result.close()


def get_highlights_from_openai(query, page_content):
    try:
        response = openai.ChatCompletion.create(  # openai.openai_object.OpenAIObject
            model="gpt-3.5-turbo-0613",
            messages=[
                {"role": "user", "content": 'for this page content "{}", can you please generate a list of highlight (max 5) about this user query "{}", each highlight item can be a max of 10 words'.format(page_content, query)},
            ],
            temperature=0,
        )
        response_message = response["choices"][0]["message"]["content"]
    except Exception as e:
        return {"error" : repr(e)}
    return {"succ": response_message}


def create_user_event(event_type, tag_name, text_content, base_url, userid):
    return {
        "event_type": event_type,
        "timestamp": int(datetime.now().timestamp() * 1000),
        "tag_name": tag_name,
        "text_content": text_content,
        "base_url": base_url,
        "userid": userid
    }


def save_in_redis(event):
    is_valid = UserEvent.validate(event)
    if is_valid:
        try:
            user_event = UserEvent(**event)
            print("event", event)
            user_event.save()
        except Exception as e:
            return {"error": repr(e)}
        else:
            return {"succ": str(event) + "has been saved"}
    else:
        return {"error": str(event)}


def includeme(config):
    # config.add_request_method(get_user_role, name="user_role", property=True)
    Migrator().run()
    # attach_sql(config)
    openai.api_key = config.registry.settings.get("openai_key")
    print("openai", openai.api_key)
