import json
from h_pyramid_sentry import report_exception
from kombu.exceptions import OperationalError
from pyramid.events import BeforeRender, subscriber

from h import __version__, emails
from h.events import AnnotationEvent, ShareflowMetadataEvent
from h.exceptions import RealtimeMessageQueueError
from h.notification import reply
from h.services.annotation_read import AnnotationReadService
from h.tasks import mailer


@subscriber(BeforeRender)
def add_renderer_globals(event):
    request = event["request"]

    event["base_url"] = request.route_url("index")
    event["feature"] = request.feature

    event["google_analytics_measurement_id"] = request.registry.settings.get(
        "google_analytics_measurement_id"
    )

    # Add a frontend settings object which will be rendered as JSON into the
    # page.
    event["frontend_settings"] = {}

    if "h.sentry_dsn_frontend" in request.registry.settings:
        event["frontend_settings"]["sentry"] = {
            "dsn": request.registry.settings["h.sentry_dsn_frontend"],
            "environment": request.registry.settings["h.sentry_environment"],
            "release": __version__,
            "userid": request.authenticated_userid,
        }


# The docs say the order isn't guaranteed but pyramid appears to execute the
# subscribers in alphabetical order. We'd like the annotation_sync() event
# first, as it's the most important. If # we have Celery problems, we don't
# want to wait behind other tasks resolving it.


@subscriber(AnnotationEvent)
def annotation_sync(event):
    """Ensure an annotation is synchronised to Elasticsearch."""

    # Checking feature flags opens a connection to the database. As this event
    # is processed after the main transaction has closed, we must open a new
    # transaction to ensure we don't leave an un-closed transaction
    with event.request.tm:
        search_index = event.request.find_service(name="search_index")
        search_index.handle_annotation_event(event)


@subscriber(AnnotationEvent)
def publish_annotation_event(event):
    """Publish an annotation event to the message queue."""
    data = {
        "action": event.action,
        "annotation_id": event.annotation_id,
        "src_client_id": event.request.headers.get("X-Client-Id"),
    }
    try:
        event.request.realtime.publish_annotation(data)

    except RealtimeMessageQueueError as err:
        report_exception(err)


@subscriber(AnnotationEvent)
def send_reply_notifications(event):
    """Queue any reply notification emails triggered by an annotation event."""

    request = event.request

    with request.tm:
        annotation = request.find_service(AnnotationReadService).get_annotation_by_id(
            event.annotation_id
        )
        notification = reply.get_notification(request, annotation, event.action)

        if notification is None:
            return

        send_params = emails.reply_notification.generate(request, notification)

        try:
            mailer.send.delay(*send_params)
        except OperationalError as err:  # pragma: no cover
            # We could not connect to rabbit! So carry on
            report_exception(err)


@subscriber(AnnotationEvent)
def add_annotation_event(event):

    request = event.request

    with request.tm:
        annotation = request.find_service(AnnotationReadService).get_annotation_by_id(
            event.annotation_id
        )
        interaction_context = ""
        for selector in annotation.target_selectors:
            if selector["type"] == "TextQuoteSelector" and "exact" in selector:
                interaction_context = selector["exact"]

        page_title = ""
        if annotation.document and annotation.document.title:
            page_title = annotation.document.title

        request.find_service(name="trace").create_server_event(
            annotation.userid,
            "annotation",
            "HIGHLIGHT" if annotation.text =="" else "ANNOTATION",
            annotation.text,
            annotation.target_uri,
            interaction_context,
            interaction_context if annotation.text =="" else annotation.text,
            event.action + " highlight" if annotation.text =="" else event.action + " annotation",
            page_title
        )

@subscriber(ShareflowMetadataEvent)
def shareflow_metadata_sync(event):
    """Ensure an shareflow metadata is synchronised to the Client."""

    data = {
        "shareflow_metadata_id": event.shareflow_metadata_id,
        "src_client_id": event.request.headers.get("X-Client-Id"),
    }
    try:
        event.request.realtime.publish_shareflow_metadata(data)

    except RealtimeMessageQueueError as err:
        report_exception(err)

@subscriber(ShareflowMetadataEvent)
def shareflow_metadata_sync_cache(event):
    """Ensure an shareflow metadata is synchronised to the Redis."""

    with event.request.tm:
        service = event.request.find_service(name="shareflow")

        groups = service.get_groups_from_shareflow_metadata_id(
            event.shareflow_metadata_id
        )
        group_ids = [group.pubid for group in groups]

        record_item_service = event.request.find_service(name="record_item")
        item = record_item_service.get_record_item_by_id(
            event.index
        )
        item.groupid = json.dumps(group_ids)

        record_item_service.init_user_event_record(item.dict())
