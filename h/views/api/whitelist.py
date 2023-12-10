from urllib.parse import urlparse

from h.models_redis import get_whitelist
from h.views.api.config import api_config


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
    return [urlparse(w.domain).netloc for w in whitelist]
