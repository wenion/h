from pyramid import httpexceptions
from pyramid.view import view_config

# from h import models
from h.models_redis import get_whitelist, get_blacklist, add_security_list, delete_security_list
from h.i18n import TranslationString as _
from h.security import Permission


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
        "whitelist": [{"name": w.name, "URL": w.domain, "type": w.methodology} for w in whitelist],
        "blacklist": [{"name": w.name, "Category": w.domain, "type": w.methodology} for w in blacklist],
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
    methodology = request.params["methodology"].strip()
    if methodology == "whitelist":
        add_security_list("whitelist", name, "url", add)
    elif methodology == "blacklist":
        add_security_list("blacklist", name, "category", add)
    else:
        request.session.flash(
            # pylint:disable=consider-using-f-string
            _("Error Authority {methodology} doesn't exist.".format(methodology=methodology)),
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
    if item["type"] == "whitelist":
        delete_security_list(item["type"], item["URL"])
    elif item["type"] == "blacklist":
        delete_security_list(item["type"], item["Category"])
    index = request.route_path("admin.security")
    return httpexceptions.HTTPSeeOther(location=index)
