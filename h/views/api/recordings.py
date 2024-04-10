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

from h.models_redis import start_user_event_record, finish_user_event_record
from h.security import Permission
from h.views.api.config import api_config

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.batch",
    link_name="batch",
    description="batch",
)
def batch(request):
    pass


@api_config(
    versions=["v1", "v2"],
    route_name="api.recordings",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="recording.create",
    description="Create an recording",
)
def create(request):
    """Create an annotation from the POST payload."""
    data = request.json_body
    print('create data', data)
    result = start_user_event_record(
        data['startstamp'],
        data['session_id'],
        data['task_name'],
        data['description'],
        data['target_uri'],
        data['start'],
        request.authenticated_userid,
        data['groupid'],
        )
    return result.dict()


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="GET",
    permission=Permission.Annotation.READ,
    link_name="recording.read",
    description="Fetch an recording",
)
def read(context, request):
    pass


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
    data = request.json_body
    # if finish
    return finish_user_event_record(context.pk, data["endstamp"]).dict()
    # other update


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="DELETE",
    permission=Permission.Annotation.DELETE,
    link_name="recording.delete",
    description="Delete an recording",
)
def delete(context, request):
    pass


