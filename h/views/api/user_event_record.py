"""
HTTP/REST API for storage and retrieval of annotation data.

This module contains the views which implement our REST API, mounted by default
at ``/api``. Currently, the endpoints are limited to:

- basic CRUD (create, read, update, delete) operations on annotations
- annotation search
- a handful of authentication related endpoints

It is worth noting up front that in general, authorization for requests made to
each endpoint is handled outside of the body of the view functions. In
particular, requests to the CRUD API endpoints are protected by the Pyramid
authorization system. You can find the mapping between annotation "permissions"
objects and Pyramid ACLs in :mod:`h.traversal`.
"""
from pyramid import i18n

from h.security import Permission
from h.traversal import UserEventRecordContext
from h.views.api.config import api_config
from h.views.api.exceptions import PayloadError
from h.tasks import shareflow

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.trackings",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
    link_name="tracking.read",
    description="Get the user viewing shareflow and scrollTop",
)
def get_trackings(request):
    track = request.session.peek_flash("tracking")
    if track and track[0]:
        return track[0]
    else:
        return { 'id': None, 'scrollToId' : None, }


@api_config(
    versions=["v1", "v2"],
    route_name="api.trackings",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="tracking.update",
    description="Update the user viewing shareflow and scrollTop",
)
def update_trackings(request):
    data = request.json_body

    request.session.pop_flash("tracking")
    request.session.flash(data, "tracking")
    return None


@api_config(
    versions=["v1", "v2"],
    route_name="api.recordings",
    request_method="GET",
    link_name="recordings.read",
    description="Fetch the user's groups",
)
def recordings(request):
    """Retrieve the groups for this request's user."""
    userid = request.authenticated_userid if request.authenticated_userid else ""

    all = request.find_service(name="shareflow").json_shareflow_metadata_search_query(
        userid = userid,
        shared = True
    )

    return all


@api_config(
    versions=["v1", "v2"],
    route_name="api.recordings",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="recording.create",
    description="Create an recording",
)
def create(request):
    """Create an record from the POST payload."""
    payload = _json_payload(request)
    data = create_validate(request, payload)

    # TODO remove
    redis_data = create_redis_validate(request, payload)
    record_item = request.find_service(name="record_item").init_user_event_record(redis_data)

    shareflow_service = request.find_service(name="shareflow")
    shareflow_metadata = shareflow_service.create_shareflow_metadata({
        **data,
        # withdraw the frontend's sessionId
        "session_id": record_item.get("id", None),
        "pk": record_item.get("id", None), # refer to record_item which stored in redis
    })

    request.session.flash(shareflow_metadata.session_id, "recordingSessionId")
    request.session.flash(shareflow_metadata.task_name, "recordingTaskName")

    return shareflow_service.present(shareflow_metadata)


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="GET",
    # permission=Permission.Annotation.READ,
    link_name="recording.read",
    description="Fetch an recording",
)
def read(context: UserEventRecordContext, request):
    user_event_record = context.user_event_record
    return request.find_service(name="record_item").basic_record_item_by_id(
        user_event_record
    )


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method=("PATCH", "PUT"),
    # permission=Permission.Annotation.UPDATE,
    link_name="recording.update",
    description="Update an recording",
)
def update(context: UserEventRecordContext, request):
    """Update the specified annotation with data from the PATCH payload."""
    data = _json_payload(request)
    shareflow_metadata = context.shareflow_metadata

    service = request.find_service(name="shareflow")
    updated = service.update_shareflow_metadata(data, shareflow_metadata)
    json_reply =service.present(updated)

    if 'endstamp' in data:
        request.session.pop_flash("recordingSessionId")
        request.session.pop_flash("recordingTaskName")
        shareflow.add_shareflow_metadata.delay(json_reply)
    return json_reply


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="DELETE",
    # permission=Permission.Annotation.DELETE,
    link_name="recording.delete",
    description="Delete an recording",
)
def delete(context, request):
    shareflow_metadata = context.shareflow_metadata
    service = request.find_service(name="shareflow")
    succ = service.delete_shareflow_metadata(shareflow_metadata)
    # TODO
    return {"id": shareflow_metadata.session_id, "deleted": succ}


def _json_payload(request):
    """
    Return a parsed JSON payload for the request.

    :raises PayloadError: if the body has no valid JSON body
    """
    try:
        return request.json_body
    except ValueError as err:
        raise PayloadError() from err


def create_validate(request, data):
    new_appstruct = {}

    new_appstruct["userid"] = request.authenticated_userid
    new_appstruct["startstamp"] = data["startstamp"]
    new_appstruct["session_id"] = data["sessionId"]
    new_appstruct["task_name"] = data["taskName"]
    new_appstruct["backdate"] = data["backdate"]
    new_appstruct["description"] = data["description"]

    # TODO
    # timezone
    return new_appstruct

def create_redis_validate(request, data):
    new_appstruct = {}

    new_appstruct["userid"] = request.authenticated_userid
    new_appstruct["startstamp"] = data["startstamp"]
    new_appstruct["endstamp"] = -1
    new_appstruct["session_id"] = data["sessionId"]
    new_appstruct["task_name"] = data["taskName"]
    new_appstruct["description"] = data["description"]
    # new_appstruct["target_uri"] = data["targetUri"]
    new_appstruct["backdate"] = data["backdate"]
    new_appstruct["completed"] = 0
    new_appstruct["groupid"] = ''
    new_appstruct["shared"] = 0

    return new_appstruct
