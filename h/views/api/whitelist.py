from urllib.parse import urlparse

from h.models_redis import get_whitelist
from h.views.api.config import api_config


def compare_string(domain, type):
    url = urlparse(domain)
    if type == 'domain' or type == 'url':
        return '.'.join(url.netloc.split('.')[-2:]).split(':')[0]
    elif type == 'hostname':
        return url.netloc.split(':')[0]
    elif type == 'host':
        return url.netloc
    elif type == 'subdirectory':
        return url.netloc + url.path


@api_config(
    versions=["v1", "v2"],
    route_name="api.whitelist",
    link_name="whitelist",
    renderer="json_sorted",
    description="URL templates for generating URLs for HTML pages",
    # nb. We assume that the returned URLs and URL templates are the same for all users,
    # regardless of authorization.
    http_cache=(60 * 5, {"public": True}),
)
def whitelist(_context, request):
    whitelist = get_whitelist()
    result = []
    for w in whitelist:
        r = compare_string(w.domain, w.type)
        if r != '':
            result.append(r)
    return result
