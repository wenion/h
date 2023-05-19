from redis_om import Migrator

from h.models_redis.user_role import UserRole

__all__ = (
    "UserRole",
)

def includeme(config):
    Migrator().run()