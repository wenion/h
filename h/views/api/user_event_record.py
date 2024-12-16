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

    all_record_items = request.find_service(name="record_item").record_item_search_query(
        userid, True
    )
    return all_record_items


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

    record_item = request.find_service(name="record_item").init_user_event_record(data)
    
    request.session.flash(record_item["sessionId"], "recordingSessionId")
    request.session.flash(record_item["taskName"], "recordingTaskName")
    return record_item


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
def update(context, request):
    """Update the specified annotation with data from the PATCH payload."""
    data = _json_payload(request)

    if 'shared' in data:
        record_item = request.find_service(name="record_item").share_user_event_record(
            context.id,
            1 if data['shared'] else 0
        )
        return record_item
    if 'endstamp' in data:
        record_item = request.find_service(name="record_item").finish_user_event_record(
            context.id,
            data['endstamp']
        )
        request.session.pop_flash("recordingSessionId")
        request.session.pop_flash("recordingTaskName")
        return record_item


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="DELETE",
    # permission=Permission.Annotation.DELETE,
    link_name="recording.delete",
    description="Delete an recording",
)
def delete(context, request):
    # Steve: delete process model when Shareflow gets deleted
    # try:
    #     tad_url = urljoin(request.registry.settings.get("tad_url"), "delete_process_model")
    #     pm_data = {"user_id": context.user_event_record.userid,
    #               "shareflow_name": context.user_event_record.task_name,
    #               "session_id": context.user_event_record.session_id}
    #     headers = {"Content-Type": "application/json"}
    #     pm_deletion_response = requests.post(tad_url, json=pm_data, headers=headers)
    #     if not pm_deletion_response["created"]:
    #         print("Unable to delete process model due to", pm_deletion_response["message"])
    # except Exception as e:
    #     print("Process model not deleted due to error:", e)
    #     pass
    succ = request.find_service(name="record_item").delete_user_event_record(context.id)
    # TODO
    return {"id": context.id, "deleted": succ}


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
