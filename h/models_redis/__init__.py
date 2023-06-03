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

__all__ = (
    "UserRole",
    "Result",
    "Bookmark",
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


def includeme(config):
    config.add_request_method(get_user_role, name="user_role", property=True)
    Migrator().run()
