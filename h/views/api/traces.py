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
from h.traversal import UserEventContext
from h.views.api.config import api_config

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
    userid = request.authenticated_userid

    result = request.find_service(name="trace").get_user_trace(userid, id)
    if not len(result):
        return request.find_service(name="trace").get_traces_by_session_id(id)
    return result


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
