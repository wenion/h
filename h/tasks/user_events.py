from h.celery import celery, get_task_logger

log = get_task_logger(__name__)


@celery.task
def job_start(event):
    pass

@celery.task
def job_finish(event):
    pass


def log_trace(event):
    tag_name = event["tagName"]
    action_type = event.get('custom', "")
    event_type = event["type"]
    task_name = "" if event.get("taskName") is None else event.get("taskName")
    label = event.get('label', "")
    userid = event.get('userid', "")

    output = '|'.join([tag_name, action_type, event_type, task_name, label, userid])
    log.info(output)


@celery.task
def add_event(event):
    """Task to add the new UserEvent table."""
    # pylint:disable=no-member
    new_appstruct = {
        'userid': event["userid"],
        'event_type': event["type"],
        'timestamp': event["timestamp"],
        'tag_name': event["tagName"],
        'text_content': event.get("textContent", ""),
        'base_url': event["url"],
        'ip_address': event.get("ipAddress", ""),
        'interaction_context': event.get("interactionContext"),
        'event_source': event["eventSource"],
        'x_path': event.get("xpath", ''),
        'offset_x': event.get("clientX"),
        'offset_y': event.get("clientY"),
        'doc_id':event.get("doc_id", ""),
        'region':event.get("region", ""),
        'session_id':event.get("sessionId"),
        'task_name':event.get("taskName"),
        'width':event.get("width"),
        'height':event.get("height"),
        'image':event.get('image'),
        'title':event.get('title'),
        'label':event.get('label'),
        'action_type':event.get('custom'),
    }
    user_dict = celery.request.find_service(name="trace").create_user_event(new_appstruct)
    log_trace(event)

    if user_dict["tag_name"] == "RECORD" and user_dict["text_content"] == "start":
        job_start.delay(event)
    if user_dict["tag_name"] == "RECORD" and user_dict["text_content"] == "finish":
        job_finish.delay(event)
