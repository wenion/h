from datetime import datetime, timezone
import json
import pytz
from h.models_redis import UserEvent


class TraceService:
    """A service for manipulating organizations."""

    def __init__(self, request):
        """
        Create a new organizations service.

        :param session: the SQLAlchemy session object
        """
        self.request = request
        self.userid = request.authenticated_userid
        self.session = request.db

    @staticmethod
    def user_event(item):
        image_src = None
        if item.image and item.image != '':
            image_src = item.pk
        return {
            'pk': item.pk,
            'userid': item.userid,
            'event_type': item.event_type,
            'timestamp': item.timestamp,
            'time': datetime.fromtimestamp(item.timestamp/1000, tz=pytz.timezone("Australia/Melbourne")),
            'tag_name': item.tag_name,
            'text_content': item.text_content,
            'base_url': item.base_url,
            'ip_address': item.ip_address,
            'interaction_context': item.interaction_context,
            'event_source': item.event_source,
            'x_path': item.x_path,
            'offset_x': item.offset_x,
            'offset_y': item.offset_y,
            'doc_id': item.doc_id,
            'system_time': item.system_time.astimezone(pytz.timezone("Australia/Sydney")) if item.system_time else None,
            'region': item.region,
            'session_id': item.session_id,
            'task_name': item.task_name,
            'width': item.width,
            'height': item.height,
            'image': image_src,
            'title': item.title,
            'label': item.label,
            'action_type': item.action_type,
        }

    @staticmethod
    def user_event_search_query(userid, offset, limit, sortby):
        query = UserEvent.find(UserEvent.userid == userid)
        results = query.copy(offset=offset, limit=limit).sort_by(sortby).execute(exhaust_results=False)

        table_result=[]
        for index, item in enumerate(results):
            json_item = {'id': index, **TraceService.user_event(item)}
            table_result.append(json_item)

        return table_result

    @staticmethod
    def get_user_event_sortable_fields():
        properties = UserEvent.schema()["properties"]
        if "image" in properties:
            properties.pop("image")
        sortable_fields = {key: value for key, value in properties.items() if 'format' not in value}
        return sortable_fields
    
    @staticmethod
    def count(userid):
        return UserEvent.find(UserEvent.userid == userid).count()

    @staticmethod
    def get_image_data_by_pk(pk):
        try:
          item = UserEvent.get(pk)
        except:
            return None
        else:
            return item.image

    @staticmethod
    def to_trace_data(item: UserEvent):
        timestamp = datetime.fromtimestamp(item.timestamp / 1000, tz=timezone.utc)

        interaction_context = None
        if isinstance(getattr(item, 'interaction_context', None), str):
            try:
                interaction_context = json.loads(item.interaction_context)
            except json.JSONDecodeError as e:
                interaction_context = None
            except:
                interaction_context = None

        image_pk = item.pk if getattr(item, 'image', None) else None
        return {
            'pk': item.pk,
            'type': item.event_type,
            'title': item.action_type,
            'description': item.label,
            'tag_name': item.tag_name,
            'width': item.width,
            'height': item.height,
            'client_x': item.offset_x,
            'client_y': item.offset_y,
            'url': item.base_url,
            'timestamp': timestamp,
            'interaction_context': interaction_context,
            'image': image_pk,
        }

    @staticmethod
    def basic_user_event(item):
        image_src = None
        if getattr(item, 'image', None):  # safer check for attribute
            image_src = getattr(item, 'pk', None)  # ensure pk exists

        if isinstance(getattr(item, 'interaction_context', None), str):
            try:
                item.interaction_context = json.loads(item.interaction_context)
            except json.JSONDecodeError as e:
                item.interaction_context = None
            except:
                item.interaction_context = None
        else:
            item.interaction_context = None

        return {
            'id': item.pk,
            'pk': item.pk,
            'type': item.event_type,
            'title': item.action_type,
            'description': item.label,
            'timestamp': item.timestamp,
            'tagName': item.tag_name,
            'interaction_context': item.interaction_context,
            # 'textContent': item.text_content,
            'width': item.width,
            'height': item.height,
            'clientX': item.offset_x,
            'clientY': item.offset_y,
            'url': item.base_url,
            'image': image_src,
        }

    def create_server_event(
        self,
        userid,
        type,
        tag,
        text_content,
        url=None,
        interaction_context=None,
        label="",
        custom="",
        page_title="",
    ):
        """Create an server-side user event."""
        session_id = None
        task_name = None
        if len(queue_session_id := self.request.session.peek_flash("recordingSessionId")) > 0:
            session_id = queue_session_id[0]
        if len(queue_task_name := self.request.session.peek_flash("recordingTaskName")) > 0:
            task_name = queue_task_name[0]

        if custom == "":
            custom = type

        new_appstruct = {
            'userid': userid,
            'event_type': type,
            'timestamp': int(datetime.now().timestamp() * 1000),
            'tag_name': tag.upper(),
            'text_content': text_content,
            'base_url': self.request.url if not url else url,
            'ip_address': "", #self.request.client_addr,
            'interaction_context': tag if not interaction_context else interaction_context,
            'event_source': "SERVER",
            # "system_time": datetime.now(timezone.utc),
            'x_path': "",
            'offset_x': None,
            'offset_y': None,
            'doc_id': "",
            'region': "",
            'session_id': session_id,
            'task_name': task_name,
            'width': 0,
            'height': 0,
            'image': None,
            'title': page_title,
            'label': label,
            'action_type': custom,
        }
        return TraceService.create_user_event(new_appstruct)
    
    @staticmethod
    def create_user_event(data):
        """Create an user event."""
        data['system_time'] = datetime.now(timezone.utc)
        trace = UserEvent(**data)
        trace.save()
        if not data['session_id']:
            trace.expire(24 * 60 * 60)
        return TraceService.user_event(trace)

    @staticmethod
    def get_traces_by_session_id_sorted(session_id: str):
        query = UserEvent.find(UserEvent.session_id == session_id)
        user_events = query.sort_by('timestamp').execute(exhaust_results=True)

        events = []
        for item in user_events:
            item_dict = {
                **TraceService.to_trace_data(item),
            }
            events.append(item_dict)

        return events


def trace_factory(_context, request):
    """Return a TraceService instance for the request."""
    return TraceService(request)
