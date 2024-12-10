import base64
from pyramid import i18n, httpexceptions
from h.views.api.config import api_config
from pyramid.response import Response

from h.security import Permission

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.image",
    request_method="GET",
    # permission=Permission.Annotation.CREATE,
    link_name="trace.image",
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
    base64_string_with_prefix = context.image
    if base64_string_with_prefix:
        base64_string = base64_string_with_prefix.split(',')[1]
        image = base64.b64decode(base64_string)
        return Response(image, content_type='image/jpeg')
    else:
        return httpexceptions.HTTPNotFound()
