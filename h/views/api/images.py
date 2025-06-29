import base64
from datetime import datetime, timedelta
from email.utils import formatdate
from pyramid import i18n, httpexceptions
from pyramid.response import Response

from h.views.api.config import api_config
from h.views.api.exceptions import PayloadError
from h.security import Permission

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.image",
    request_method="GET",
    # permission=Permission.Annotation.CREATE,
    link_name="image.read",
    description="Get a trace's image",
)
def read(context, request):
    # token_svc = request.find_service(name="auth_token")
    # token_str = None

    # token_str = request.GET.get("access_token", None)

    # if token_str is None:
    #     token_str = token_svc.get_bearer_token(request)

    # if token_str is None:
    #     return httpexceptions.HTTPNotFound()

    # token = token_svc.validate(token_str)
    # if token is None:
    #     return httpexceptions.HTTPNotFound()

    # user = request.find_service(name="user").fetch(token.userid)
    # if user is None or user.deleted:
    #     return httpexceptions.HTTPNotFound()

    # print('user', user)
    shareflow_image = context.image
    if shareflow_image:
        one_year_from_now = datetime.utcnow() + timedelta(days=365)
        expires_http = formatdate(timeval=one_year_from_now.timestamp(), usegmt=True)
        response = Response(
            shareflow_image.image_data,
            content_type='image/jpeg'
        )
        response.headers.update({
            'Cache-Control': 'public, max-age=31536000, immutable',
            'Expires': expires_http,
            # Optional:
            'ETag': '"541-v1"',  # you can hash the file content for dynamic etags
        })
        return response
    else:
        return httpexceptions.HTTPNotFound()


@api_config(
    versions=["v1", "v2"],
    route_name="api.image",
    request_method=("PATCH", "PUT"),
    permission=Permission.Profile.UPDATE,
    link_name="image.update",
    description="Update a trace's image",
)
def update(context, request):
    shareflow_image = context.image
    user = request.user

    params = _json_payload(request)

    updated = params.get('image')

    if shareflow_image and updated:
        shareflow_image.set_image(updated)
        one_year_from_now = datetime.utcnow() + timedelta(days=365)
        expires_http = formatdate(timeval=one_year_from_now.timestamp(), usegmt=True)
        response = Response(
            shareflow_image.image_data,
            content_type='image/jpeg'
        )
        response.headers.update({
            'Cache-Control': 'public, max-age=31536000, immutable',
            'Expires': expires_http,
            # Optional:
            'ETag': '"541-v1"',  # you can hash the file content for dynamic etags
        })
        return response


def _json_payload(request):
    """
    Return a parsed JSON payload for the request.

    :raises PayloadError: if the body has no valid JSON body
    """
    try:
        return request.json_body
    except ValueError as err:
        raise PayloadError() from err
