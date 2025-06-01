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
import json
from pyramid import i18n
from pyramid.httpexceptions import HTTPBadRequest

from h.security import Permission
from h.views.api.config import api_config

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.histories",
    request_method="GET",
    permission=Permission.Profile.UPDATE,
    link_name="histories.read",
    description="Fetch the shareflow's version histories",
)
def get_version_list(request):
    id = request.GET.get('id')
    if id is None:
        return HTTPBadRequest()

    version_service = request.find_service(name="version_control")
    version_meta = version_service.get(id)
    if version_meta:
        return version_service.history(version_meta.pk)
    return []


@api_config(
    versions=["v1", "v2"],
    route_name="api.history",
    request_method="GET",
    permission=Permission.Profile.UPDATE,
    link_name="history.read",
    description="Fetch the shareflow's version traces",
)
def get_version_traces(request):
    id = request.GET.get('id')
    version = request.GET.get('version')

    if id is None or version is None or not version.isdigit():
        raise HTTPBadRequest()

    version = int(version)

    version_service = request.find_service(name="version_control")
    version_meta = version_service.get(id)
    if version_meta:
        version_service.downgrade(version_meta.pk, version)
        node = version_service.head(id)
        if node:
            data = json.loads(node.data)
            return data

    return []


@api_config(
    versions=["v1", "v2"],
    route_name="api.histories",
    request_method="DELETE",
    # permission=Permission.Profile.UPDATE,
    link_name="histories.delete",
    description="Delete cache",
)
def delete(request):
    id = request.GET.get('id')
    if id is None:
        raise HTTPBadRequest()

    version_service = request.find_service(name="version_control")
    version_meta = version_service.get(id)
    succ = False
    if version_meta:
        version_service.delete(version_meta.pk)
        succ = True

    return {"id": id, "deleted": succ}