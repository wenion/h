from datetime import datetime, timezone
import re

from h import util
from h.exceptions import InvalidUserId
from h.models_redis import (
    create_message_cache,
    fetch_message_cache_by_user_id,
    get_message_cache,
)
from h.services.organisation_event import OrganisationEventService
from h.services.organisation_event_push_log import OrganisationEventPushLogService



class MessageService:
    def __init__(
        self,
        request,
        organisation_event_service,
    ):
        self.request = request
        self.userid = request.authenticated_userid
        self.organisation_event_service = organisation_event_service

    @staticmethod
    def _split_user(userid):
        """
        Return the user and domain parts from the given user id as a dict.

        For example if userid is u'acct:seanh@hypothes.is' then return
        {'username': u'seanh', 'domain': u'hypothes.is'}'

        :raises InvalidUserId: if the given userid isn't a valid userid

        """
        match = re.match(r"^acct:([^@]+)@(.*)$", userid)
        if match:
            return {"username": match.groups()[0], "domain": match.groups()[1]}
        raise InvalidUserId(userid)

    def _make_message(
        self,
        type,
        pubid,
        event_name,
        message,
        date = datetime.now().strftime("%s%f"),
        show_flag = True,
        unread_flag = True,
        need_save_flag=True,
        extra = None
    ):
        return {
            'type': type,
            'id': pubid,
            'title': event_name,
            'message': message,
            'date': date,
            'show_flag': show_flag,
            'unread_flag': unread_flag,
            'need_save_flag': need_save_flag,
            'extra': extra,
        }

    def read(self, userid):
        result = []

        # get organisation event messages
        day_ahead = 3
        all = self.organisation_event_service.get_by_date_in_ahead(day_ahead)
        for item in all:
            result.append(
                self._make_message(
                    "organisation_event",
                    item.pubid,
                    item.event_name,
                    item.text,
                    item.date.replace(tzinfo=timezone.utc).astimezone().strftime("%s%f"),
                    False,
                    False,
                )
            )

        # get redis message
        caches = fetch_message_cache_by_user_id(userid)
        for cache in caches:
            result.append(self._make_message(
                cache.type,
                cache.id,
                cache.title,
                cache.message,
                cache.date,
                False,
                False,
                True,
                cache.extra,
            ))

        return result

    def add_message_cache(self, payload, userid, identifier):
        now = datetime.now()
        id = now.strftime("%S%M%H%d%m%Y") + "_"
        if userid:
            id = id + util.user.split_user(userid)["username"]
        else:
            id = id + identifier

        m = create_message_cache(
            "instant_message",
            id,
            payload['title'],
            payload['content'],
            now.strftime("%s%f"),
            True,
            True,
            True,
            payload['extra'],
            payload['url'],
            userid if userid else identifier,
            int(now.timestamp()),# timestamp,
            ""
        )
        return get_message_cache(m.pk)

def message_service_factory(_context, request) -> MessageService:
    return MessageService(
        request,
        organisation_event_service=request.find_service(name="organisation_event"),
    )
