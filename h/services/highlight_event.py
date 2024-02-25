from redis_om import get_redis_connection


class HighlightEventService:
    """A service for manipulating highlight event."""

    def __init__(self):
        """
        Create a new highlight event service.

        :param session: the Redis session object
        """
        self.key = "h:Recommendation:"
        self.session = get_redis_connection()

    def create(self, username, url, data, expire=120):
        key = self.key + username + ":" + url
        self.session.set(key, data)
        self.session.expire(key, expire)
        return key
    
    def get_by_username_and_url(self, username, url):
        key = self.key + username + ":" + url
        value = self.session.getdel(key)
        return value


def highlight_event_factory(_context, request):
    """Return a HighlightEventService instance for the request."""
    return HighlightEventService()