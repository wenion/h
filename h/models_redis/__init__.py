from redis_om import Migrator


__all__ = ()

def includeme(config):
    Migrator().run()