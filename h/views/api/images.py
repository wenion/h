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
import base64
from pyramid import i18n, httpexceptions
from pyramid.view import view_config
from pyramid.response import Response

from h.security import Permission

_ = i18n.TranslationStringFactory(__package__)


@view_config(
    route_name="api.image",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
)
def read(context, request):
    # print("context", context)
    base64_string_with_prefix = context.image
    if base64_string_with_prefix:
        base64_string = base64_string_with_prefix.split(',')[1]
        image = base64.b64decode(base64_string)
        return Response(image, content_type='image/jpeg')
    else:
        return httpexceptions.HTTPNotFound()
