import openai

from redis_om import Migrator
from redis_om import Field, JsonModel, EmbeddedJsonModel
from pydantic import NonNegativeInt
from typing import Optional


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

def get_user_role_by_userid(userid):
    user_role = UserRole.find(
        UserRole.userid == userid
        ).all()
    if len(user_role) == 1:
        return user_role[0]
    else:
        return None


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
        user_role.save()


def attach_sql(config):
    engine = config.registry["sqlalchemy.engine"]
    result = engine.execute('SELECT username, authority FROM public."user";')
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


def includeme(config):
    config.add_request_method(get_user_role, name="user_role", property=True)
    Migrator().run()
    attach_sql(config)
    openai.api_key = config.registry.settings.get("openai_key")
    print("openai", openai.api_key)
