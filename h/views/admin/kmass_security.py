from pyramid import httpexceptions
from pyramid.view import view_config
from urllib.parse import urlparse

# from h import models
from h.models_redis import get_whitelist, get_blacklist, add_security_list, delete_security_list
from h.i18n import TranslationString as _
from h.security import Permission


def compare_string(domain, type):
    url = urlparse(domain)
    if url.scheme != 'http' or url.scheme != 'http' or (url.scheme =='' and url.netloc == ''):
        return 'error url'
    elif type == 'domain' or type == 'url':
        return '.'.join(url.netloc.split('.')[-2:]).split(':')[0]
    elif type == 'hostname':
        return url.netloc.split(':')[0]
    elif type == 'host':
        return url.netloc
    elif type == 'subdirectory':
        return url.netloc + url.path
    else:
        return 'invalid type'


@view_config(
    route_name="admin.security",
    request_method="GET",
    renderer="h:templates/admin/kmass-security.html.jinja2",
    permission=Permission.AdminPage.HIGH_RISK,
)
def staff_index(request):
    """Get a list of all the staff members as an HTML page."""
    whitelist = get_whitelist()
    blacklist = get_blacklist()
    return {
        "whitelist": [{"name": w.name, "URL": w.domain, "match": compare_string(w.domain, w.type), "type": w.type} for w in whitelist],
        "blacklist": [{"name": w.name, "Category": w.domain, "type": w.methodology} for w in blacklist],
        "options": [
            {'description': 'domain', 'value': 'domain'},
            {'description': 'hostname', 'value': 'hostname'},
            {'description': 'host', 'value': 'host'},
            {'description': 'subdirectory', 'value': 'subdirectory'}
            ]
    }


@view_config(
    route_name="admin.security",
    request_method="POST",
    request_param="add",
    renderer="h:templates/admin/kmass-security.html.jinja2",
    permission=Permission.AdminPage.HIGH_RISK,
    require_csrf=True,
)
def staff_add(request):
    """Make a given user a staff member."""
    add = request.params["add"].strip()
    name = request.params["name"].strip()
    type = request.params["methodology"].strip()
    # print("add", add, name, type)
    if type == "domain" or type == "hostname" or type == "host" or type == "subdirectory":
        comp = compare_string(add, type)
        if comp == "error url" or comp == "invalid type":
            request.session.flash(
                # pylint:disable=consider-using-f-string
                _("Error Type {url} doesn't exist.".format(url=add)),
                "error",
            )
        else:
            add_security_list("whitelist", name, type, add)
    elif type == "blacklist":
        add_security_list("blacklist", name, "category", add)
    else:
        request.session.flash(
            # pylint:disable=consider-using-f-string
            _("Error Type {type} doesn't exist.".format(type=type)),
            "error",
        )

    index = request.route_path("admin.security")
    return httpexceptions.HTTPSeeOther(location=index)


@view_config(
    route_name="admin.security",
    request_method="POST",
    request_param="remove",
    renderer="h:templates/admin/kmass-security.html.jinja2",
    permission=Permission.AdminPage.HIGH_RISK,
    require_csrf=True,
)
def staff_remove(request):
    """Remove a user from the staff."""
    item = eval(request.params["remove"])
    if item["type"] == "blacklist":
        delete_security_list(item["type"], item["Category"])
    else:
        delete_security_list('whitelist', item["URL"])
    index = request.route_path("admin.security")
    return httpexceptions.HTTPSeeOther(location=index)
