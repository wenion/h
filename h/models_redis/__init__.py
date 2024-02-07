from datetime import datetime, timezone
import math
import pytz
import openai

from redis_om import Migrator
from redis_om import Field, JsonModel, EmbeddedJsonModel
from pydantic import NonNegativeInt
from typing import Optional

from h.models_redis.rating import Rating

__all__ = (
    "UserRole",
    "Result",
    "Bookmark",
    "UserEvent",
    "Rating",
    "UserFile",
)


class UserRole(EmbeddedJsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'UserRole'
    userid: str = Field(index=True)
    faculty: str = Field(index=True)
    teaching_role: str = Field(index=True)
    teaching_unit: str = Field(index=True)
    campus: Optional[str] = Field(full_text_search=True, sortable=True)
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


class UserStatus(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'UserStatus'
    userid: str = Field(index=True)
    task_name: str = Field(index=True)
    session_id: str = Field(index=True)
    description: str = Field(index=True)
    doc_id: Optional[str] = Field(full_text_search=True, sortable=True)


def get_user_status_by_userid(userid):
    total = UserStatus.find(
        UserStatus.userid == userid
        ).all()
    if len(total):
        return total[0]
    else:
        user_status = UserStatus(
            userid=userid,
            task_name="",
            session_id="",
            description="",
            doc_id = ""
        )
        user_status.save()
        return user_status


def set_user_status(userid, task_name, session_id, description):
    user_status = get_user_status_by_userid(userid)

    user_status.task_name = task_name
    user_status.session_id = session_id
    user_status.description = description
    user_status.save()


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
        offset_x,
        offset_y,
        doc_id,
        region,
        session_id=None,
        task_name=None,
        width=0,
        height=0,
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
        offset_x=offset_x,
        offset_y=offset_y,
        doc_id=doc_id,
        system_time=datetime.utcnow().replace(tzinfo=pytz.utc),
        region=region,
        session_id=session_id,
        task_name=task_name,
        width=width,
        height=height,
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
        # 'time': datetime.utcfromtimestamp(user_event.timestamp/1000).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'time': datetime.utcfromtimestamp(user_event.timestamp/1000).replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Australia/Sydney")).strftime('%Y-%m-%d %H:%M:%S %Z'),
        'tag_name': user_event.tag_name,
        'text_content': user_event.text_content,
        'base_url': user_event.base_url,
        'ip_address': user_event.ip_address,
        'interaction_context': user_event.interaction_context,
        'event_source': user_event.event_source,
        'x_path': user_event.x_path,
        'offset_x': user_event.offset_x,
        'offset_y': user_event.offset_y,
        'doc_id': user_event.doc_id,
        'system_time': user_event.system_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Australia/Sydney")) if user_event.system_time else None,
        'region': user_event.region,
        'session_id': user_event.session_id,
        'task_name': user_event.task_name,
        'width': user_event.width,
        'height': user_event.height,
    }

def fetch_all_user_events_by_session(userid,sessionID):
    result = UserEvent.find((UserEvent.userid == userid) & (UserEvent.session_id == sessionID)).sort_by("timestamp").all()
    #.sort_by("-timestamp")
    table_result=[]
    for index, item in enumerate(result):
        json_item = {'id': index, **get_user_event(item.pk)}
        table_result.append(json_item)
    #print(table_result)  
    return {
        "table_result": table_result,
        "total": len(result),
        }

def fetch_all_user_sessions(userid):
    result = UserEvent.find(UserEvent.userid == userid).sort_by("session_id").all()

    auxSessionIds=[]
    table_result=[]
    for index, item in enumerate(result):
        json_item = {'id': index, **get_user_event(item.pk)}
        if json_item['session_id'] is not None and json_item['session_id']!="" and json_item['task_name'] is not None and json_item['task_name']!="":
            if not auxSessionIds:
                table_result.append(json_item)
                auxSessionIds.append(json_item['session_id'])
                print("INIT session: "+json_item['session_id'])
            else:
                flag=True
                for sesionid in auxSessionIds:
                    if sesionid==json_item['session_id']:
                        flag=False
                if flag:
                    table_result.append(json_item)
                    auxSessionIds.append(json_item['session_id'])
                    print("INIT session: "+json_item['session_id'])
    #print("Num: "+ str(len(result))) 
    return {
        "table_result": table_result,
        "total": len(result),
        }

# class Rating(JsonModel):
#     class Meta:
#         global_key_prefix = 'h'
#         model_key_prefix = 'Rating'
#     created_timestamp: int = Field(index=True)
#     updated_timestamp: int = Field(index=True)
#     relevance: str = Field(index=True)
#     timeliness: str = Field(index=True)
#     base_url: str = Field(index=True)
#     userid: str = Field(index=True)


def fetch_all_user_event(userid, sortby):
    result = UserEvent.find(
        UserEvent.userid == userid
    ).sort_by(sortby).all()
    table_result=[]
    for index, item in enumerate(result):
        json_item = {'id': index, **get_user_event(item.pk)}
        table_result.append(json_item)
    return {
        "table_result": table_result,
        "total": len(result),
        }


def fetch_user_event(userid, offset, limit, sortby):
    query = UserEvent.find(
        UserEvent.userid == userid
        )
    total = len(query.all())
    # if offset > math.ceil(total / limit):
    #     offset = math.ceil(total / limit)

    results = query.copy(offset=offset, limit=limit).sort_by(sortby).execute(exhaust_results=False)

    table_result=[]
    for index, item in enumerate(results):
        json_item = {'id': index, **get_user_event(item.pk)}
        table_result.append(json_item)
    return {
        "table_result": table_result,
        "total": total,
        "offset": offset,
        "limit": limit,
        }


def get_user_event_sortable_fields():
    properties = UserEvent.schema()["properties"]
    sortable_fields = {key: value for key, value in properties.items() if 'format' not in value}
    return sortable_fields


class SecurityList(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'SecurityList'
    methodology : str = Field(index=True) # black white
    name: str = Field(index=True)
    type: str = Field(index=True) # url
    category: Optional[str] = Field(full_text_search=True, sortable=True)
    domain: str = Field(full_text_search=True,)


def get_whitelist():
    return SecurityList.find(
        SecurityList.methodology == 'whitelist'
    ).all()


def get_blacklist():
    return SecurityList.find(
        SecurityList.methodology == 'blacklist'
    ).all()


def add_security_list(methodology, name, type, domain):
    exist = SecurityList.find(
        (SecurityList.methodology == methodology) &
        (SecurityList.domain == domain)
    ).all()
    if len(exist) > 0:
        return exist[0]
    user_event = SecurityList(
        methodology=methodology,
        name=name,
        type=type,
        domain=domain,
    )
    user_event.save()
    return user_event


def delete_security_list(methodology, domain):
    exist = SecurityList.find(
        (SecurityList.methodology == methodology) &
        (SecurityList.domain == domain)
    ).all()
    if len(exist) > 0:
        SecurityList.delete(exist[0].pk)


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


def add_user_role(userid, faculty, role, unit, campus, year, experience, expert):
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
            campus=campus,
            joined_year=year,
            years_of_experience=experience,
            expert=expert
        )
        user_role.save()
        return user_role


def update_user_role(userid, faculty, role, unit, campus, year, experience, expert):
    user_roles = UserRole.find(
        UserRole.userid == userid
        ).all()
    if len(user_roles):
        user_role = user_roles[0]
        user_role.faculty = faculty
        user_role.teaching_role = role
        user_role.teaching_unit = unit
        user_role.campus = campus
        user_role.joined_year = year
        user_role.years_of_experience = experience
        if expert:
            user_role.expert = expert
        user_role.save()
        return True
    else:
        return False


def get_user_role_by_userid(userid):
    return add_user_role(userid, "", "", "", "", 0, 0, 0)


def get_user_role(request):
    """
    Return the user for the request or None.

    :rtype: h.models.User or None

    """
    if request.authenticated_userid is None:
        return None
    user_role = get_user_role_by_userid(request.authenticated_userid)

    return user_role


# def check_redis_keys(username, authority):
#     userid = f"acct:{username}@{authority}"
#     user_role = UserRole.find(
#         UserRole.userid == userid
#     ).all()

#     if not len(user_role):
#         user_role_kwargs = {
#             "userid": userid,
#             "faculty": "",
#             "teaching_role": "",
#             "teaching_unit": "",
#             "campus": "",
#             "joined_year": 0,
#             "years_of_experience": 0,
#             "expert": 0,
#         }
#         user_role = UserRole(**user_role_kwargs)
#         # user_role.save()


# def attach_sql(config):
#     engine = config.registry["sqlalchemy.engine"]
#     try:
#         result = engine.execute('SELECT username, authority FROM public."user";')
#     except Exception as e:
#         log.exception("unable to attach sql")
#     else:
#         rows = result.fetchall()
#         for row in rows:
#             check_redis_keys(row[0], row[1])
#         result.close()


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
