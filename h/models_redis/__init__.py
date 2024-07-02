from datetime import datetime, timezone
import math
import openai

from redis_om import Migrator
from redis_om import Field, JsonModel
from pydantic import NonNegativeInt
from typing import Optional

from h.models_redis.user_role import UserRole
from h.models_redis.user_event import UserEvent
from h.models_redis.user_event import fetch_all_user_event, fetch_user_event, get_user_event_sortable_fields
from h.models_redis.user_event import add_user_event, get_user_event, del_user_event, update_user_event, fetch_user_event_by_timestamp
from h.models_redis.user_event_record import UserEventRecord
from h.models_redis.user_event_record import start_user_event_record, finish_user_event_record, fetch_user_event_record_by_session_id
from h.models_redis.user_event_record import update_user_event_record, delete_user_event_record, batch_user_event_record, fetch_user_event_record_by_session
from h.models_redis.result import Result
from h.models_redis.rating import Rating
from h.models_redis.process_model import ProcessModel, fetch_all_process_model, fetch_process_model_by_session_creator, get_process_model, create_process_model, update_process_model, delete_process_model_by_session_creator, delete_process_model
from h.models_redis.task_page import TaskPage, is_task_page, fetch_all_task_pages, fetch_task_page_name_id, add_task_page, delete_task_page, delete_task_page_name_id
from h.models_redis.push_record import PushRecord, add_push_record, fetch_push_record, delete_push_record, has_three_push, same_as_previous

__all__ = (
    "UserRole",
    "Result",
    "Bookmark",
    "UserEvent",
    "UserEventRecord",
    "add_user_event",
    "get_user_event",
    "update_user_event",
    "fetch_all_user_event",
    "fetch_user_event_by_timestamp",
    "del_user_event",
    "fetch_user_event",
    "get_user_event_sortable_fields",
    "start_user_event_record",
    "finish_user_event_record",
    "fetch_user_event_record_by_session_id",
    "fetch_user_event_record_by_session",
    "update_user_event_record",
    "delete_user_event_record",
    "batch_user_event_record",
    "Rating",
    "UserFile",
    "ProcessModel",
    "fetch_all_process_model",
    "fetch_process_model_by_session_creator",
    "get_process_model",
    "create_process_model",
    "update_process_model",
    "delete_process_model",
    "delete_process_model_by_session_creator",
    "TaskPage",
    "is_task_page",
    "fetch_all_task_pages",
    "fetch_task_page_name_id",
    "add_task_page",
    "delete_task_page_name_id",
    "delete_task_page",
    "PushRecord",
    "add_push_record",
    "delete_push_record",
    "fetch_push_record",
    "has_three_push",
    "same_as_previous"
)


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
    result = UserEvent.find(UserEvent.userid == userid).sort_by("-timestamp").all()

    auxSessionIds=[]
    table_result=[]
    for index, item in enumerate(result):
        json_item = {'id': index, **get_user_event(item.pk)}
        if json_item['session_id'] is not None and json_item['session_id']!="" and json_item['task_name'] is not None and json_item['task_name']!="":
            if not auxSessionIds:
                table_result.append(json_item)
                auxSessionIds.append(json_item['session_id'])
            else:
                flag=True
                for sesionid in auxSessionIds:
                    if sesionid==json_item['session_id']:
                        flag=False
                if flag:
                    table_result.append(json_item)
                    auxSessionIds.append(json_item['session_id'])
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
    if not userid:
        return None
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
    node = {
        "event_type": event_type,
        "timestamp": int(datetime.now().timestamp() * 1000),
        "tag_name": tag_name,
        "text_content": text_content,
        "base_url": base_url,
        "userid": userid
    }
    _save_in_redis(node)


def _save_in_redis(event):
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
