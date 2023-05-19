from redis_om import (Field, JsonModel)
from pydantic import PositiveInt

from h.util.user import split_user

class UserRole(JsonModel):
    userid: str = Field(index=True)

    faculty: str = Field(index=True)
    teaching_role: str = Field(index=True)
    teaching_unit: str = Field(index=True)
    joined_year: PositiveInt = Field(index=True)
    years_of_experience: PositiveInt = Field(index=True)