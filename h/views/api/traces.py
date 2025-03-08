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
from pyramid.httpexceptions import HTTPBadRequest

from h.security import Permission
from h.services.trace_model import address_events
from h.traversal import UserEventContext
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
    id = request.GET.get('id')
    if id is None:
        return HTTPBadRequest()
    userid = request.authenticated_userid

    # result = request.find_service(name="trace").get_user_trace(userid, id)
    # if not len(result):
    result = request.find_service(name="trace").get_traces_by_session_id(id)
    return address_events(result)


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

    result = request.find_service(name="shareflow").get_shareflows_by_session_id(id)
    return result


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

    shareflow_service = request.find_service(name="shareflow")
    pre = shareflow_service.get_shareflows_by_session_id(id)
    cur = payload.values()

    ids_pre = {item["id"] for item in pre}
    ids_cur = {item["id"] for item in cur}
    ids_com = ids_pre & ids_cur

    remove = [item for item in pre if item['id'] not in ids_cur]
    append = [item for item in cur if item['id'] not in ids_pre]
    both = [item for item in cur if item['id'] in ids_com]

    for item in remove:
        shareflow = shareflow_service.read_shareflow_by_id(item["id"])
        shareflow_service.delete_shareflow(shareflow)

    if len(append):
        pass

    for item in both:
        shareflow = shareflow_service.read_shareflow_by_id(item["id"])
        update = {
            "type": item["type"],
            "title": item["title"],
            "description": item["description"],
            "url": item["url"],
        }
        if shareflow.type != update["type"] or \
            shareflow.title != update["title"] or \
            shareflow.description != update["description"] or \
            shareflow.url != update["url"]:
            shareflow = shareflow_service.update_shareflow(shareflow, **update)

    return shareflow_service.get_shareflows_by_session_id(id)


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
