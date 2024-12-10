import openai

from redis_om import Field, JsonModel
from pydantic import NonNegativeInt
from typing import Optional

from h.models_redis.user_role import UserRole
from h.models_redis.user_event import UserEvent
from h.models_redis.user_event_record import UserEventRecord
from h.models_redis.result import Result
from h.models_redis.rating import Rating
from h.models_redis.message_cache import (
    MessageCache,
    get_message_cache,
    create_message_cache,
    fetch_message_cache_by_user_id
)

__all__ = (
    "UserRole",
    "Result",
    "Bookmark",
    "UserEvent",
    "UserEventRecord",
    "Rating",
    "UserFile",
    "MessageCache",
    "get_message_cache",
    "create_message_cache",
    "fetch_message_cache_by_user_id",
)


class Bookmark(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'Bookmark'
    query: str = Field(index=True, full_text_search=True)
    user: UserRole                      # UserRole pk
    result: str = Field(index=True)     # Result pk
    deleted: int = Field(index=True, default=0)


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


def includeme(config):
    # config.add_request_method(get_user_role, name="user_role", property=True)
    # Migrator().run()
    pass
