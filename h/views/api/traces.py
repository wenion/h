"""
HTTP/REST API for storage and retrieval of shareflow data.

This module contains the views which implement our REST API, mounted by default
at ``/api``. Currently, the endpoints are limited to:

- basic CRUD (create, read, update, delete) operations on shareflows
- shareflow search
- a handful of authentication related endpoints

It is worth noting up front that in general, authorization for requests made to
each endpoint is handled outside of the body of the view functions. In
particular, requests to the CRUD API endpoints are protected by the Pyramid
authorization system. You can find the mapping between shareflow "permissions"
objects and Pyramid ACLs in :mod:`h.traversal`.
"""
from pyramid import i18n
from pyramid.httpexceptions import HTTPBadRequest

from h.events import ShareflowDataListEvent
from h.security import Permission
from h.traversal import UserEventContext
from h.util.datetime import timestamp_ms_to_utc
from h.views.api.config import api_config
from h.views.api.exceptions import PayloadError

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.traces",
    request_method="GET",
    permission=Permission.Profile.UPDATE,
    link_name="traces.read",
    description="Fetch the user's traces",
)
def traces(request):
    """Retrieve the traces for this request's user event record."""
    return get_traces(request)


@api_config(
    versions=["v1", "v2"],
    route_name="api.traces",
    request_method="GET",
    request_param="response_mode=metadata",
    permission=Permission.Profile.UPDATE,
    link_name="traces.read",
    description="Fetch the user's traces",
)
def get_traces(request):
    """Retrieve the traces for this request's user event record."""
    id = request.GET.get('id')
    if id is None:
        return HTTPBadRequest()

    service = request.find_service(name="shareflow")
    shareflow_metadata = service.get_shareflow_metadata_by_session_id(id)

    if shareflow_metadata is None:
        raise HTTPBadRequest()

    all = service.get_shareflows(shareflow_metadata)

    return [
        service.present_shareflow_for_user(shareflow)
        for shareflow in all
    ]


@api_config(
    versions=["v1", "v2"],
    route_name="api.traces",
    request_method=("PATCH", "PUT"),
    # permission=Permission.Annotation.READ,
    link_name="traces.update",
    description="Update a list of traces",
)
def update_traces(request):
    id = request.GET.get('id')
    if id is None:
        return HTTPBadRequest()
    payload = _json_payload(request)
    cur = payload.values()

    service = request.find_service(name="shareflow")
    shareflow_metadata = service.get_shareflow_metadata_by_session_id(id)
    # shareflow_metadata.version = shareflow_metadata.version + 1
    _pre = service.get_shareflows(shareflow_metadata)
    pre = [service.present_shareflow_for_user(item) for item in _pre]

    ids_pre = {item["id"] for item in pre}
    ids_cur = {item["id"] for item in cur}
    ids_com = ids_pre & ids_cur

    remove = [item for item in pre if item["id"] not in ids_cur]
    append = [item for item in cur if item["id"] not in ids_pre]
    both = [item for item in cur if item["id"] in ids_com]

    for item in remove:
        shareflow = service.get_shareflow_by_id(item.id)
        service.delete_shareflow(shareflow)

    if len(append):
        for trace in append:
            requirements = [
                'index', 'pk', 'type', 'title', 'description', 'timestamp',
                'tag_name', 'width', 'height', 'client_x', 'client_y', 'url',
                'version', 'metadata_id', 'image_id', 'user_id',
            ]
            filtered_data = {key: trace[key] for key in requirements if key in trace}

            filtered_data['timestamp'] = timestamp_ms_to_utc(filtered_data['timestamp'])
            filtered_data['tag_name'] = 'CLIENT'

            user = shareflow_metadata.user
            service.create_shareflow_from_cache(
                filtered_data,
                user,
                shareflow_metadata,
                filtered_data['index'],
                shareflow_metadata.version,
                None
            )

    for item in both:
        shareflow = service.get_shareflow_by_id(item["id"])
        shareflow.type = item["type"]
        shareflow.title = item["title"]
        shareflow.description = item["description"]
        shareflow.url = item["url"]
        shareflow.index = item["index"]
        # shareflow.version = shareflow_metadata.version

    all = service.get_shareflows(shareflow_metadata)
    readable_shareflow = [
        service.present_shareflow_for_user(shareflow)
        for shareflow in all
    ]

    data = service.present_shareflow_meta_for_user(shareflow_metadata)
    _publish_shareflow_event(request, data)

    return readable_shareflow


@api_config(
    versions=["v1", "v2"],
    route_name="api.traces",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="trace.create",
    description="Create a record",
)
def create(request):
    """Create an annotation from the POST payload."""
    return None


@api_config(
    versions=["v1", "v2"],
    route_name="api.trace",
    request_method="GET",
    # permission=Permission.Annotation.READ,
    link_name="trace.read",
    description="Fetch a trace",
)
def read(context: UserEventContext, request):
    trace = context.user_event
    return request.find_service(name="trace").basic_user_event(trace)


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
    try:
        new_appstruct = {}

        new_appstruct["userid"] = request.authenticated_userid
        new_appstruct["index"] = data["index"]
        new_appstruct["title"] = data["title"]
        new_appstruct["description"] = data["description"]
        new_appstruct["url"] = data["url"]
    except Exception as e:
        raise HTTPBadRequest

    # TODO
    # timezone
    return new_appstruct

def _publish_shareflow_event(request, data):
    """Publish an event to the shareflow queue for this shareflow action."""
    event = ShareflowDataListEvent(
        request,
        data,
    )
    request.notify_after_commit(event)
