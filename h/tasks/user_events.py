from h.celery import celery, get_task_logger
from h.models_redis import add_user_event

log = get_task_logger(__name__)


@celery.task
def add_event(userid, event):
    """Task to add the new UserEvent table."""
    # pylint:disable=no-member
    add_user_event(
        userid=userid,
        event_type=event["type"],
        timestamp=event["timestamp"],
        tag_name=event["tagName"],
        text_content=event.get("textContent", ""),
        base_url=event["url"],
        ip_address=event["ip_address"],
        interaction_context=event.get("interactionContext"),
        event_source=event["eventSource"],
        x_path=event.get("xpath"),
        offset_x=event.get("clientX"),
        offset_y=event.get("clientY"),
        doc_id=event.get("doc_id"),
        region="",
        session_id=event.get("session_id"),
        task_name=event.get("task_name"),
        width=event.get("width"),
        height=event.get("height"),
        image=event.get('image'),
        title=event.get('title'),
        )