"""Activity pages views."""

import csv
import math
from io import StringIO

from pyramid import response
from pyramid.view import view_config, view_defaults

from h import util
from h.exceptions import InvalidUserId
from h.i18n import TranslationString as _
from h.models_redis import fetch_user_event, get_user_event_fields, fetch_all_user_event

PAGE_SIZE = 25
SORT_BY = "timestamp"
ORDER = "desc"

def paginate(request, total, page_size):  # pylint:disable=too-complex
    first = 1
    page_max = int(math.ceil(total / page_size))
    page_max = max(1, page_max)  # There's always at least one page.

    try:
        current_page = int(request.params["page"])
    except (KeyError, ValueError):
        current_page = 1
    current_page = max(1, current_page)
    current_page = min(current_page, page_max)

    next_ = current_page + 1 if current_page < page_max else None
    prev = current_page - 1 if current_page > 1 else None

    # Construct the page_numbers array so that the first and the
    # last pages are always shown. There should be at most 3 pages
    # to the left and 3 to the right of the current page. Any more
    # pages than that are represented by ellipses on either side.
    # Ex: [1, '...',27, 28, 29, 30, 31, 32, 33, '...', 60]

    page_numbers = []
    buffer = 3

    # Add the first page.
    if first < current_page:
        page_numbers.append(first)

    # If there are more than 3 pages to the left of current, add the
    # ellipsis.
    max_left = current_page - buffer

    if (max_left - first) > 1:
        page_numbers.append("...")

    # If there are 1-3 pages to the left of current, add the pages.
    i = current_page - buffer
    while max_left <= i < current_page:
        if i > first:
            page_numbers.append(i)
        i += 1

    # Add the current page.
    page_numbers.append(current_page)

    # If there are 1-3 pages to the right of current, add the pages.
    max_right = current_page + buffer

    i = current_page + 1
    while current_page < i <= max_right and i < page_max:
        page_numbers.append(i)
        i += 1

    # If there are more than 3 pages to the right of current, add the
    # ellipsis.
    if (page_max - max_right) > 1:
        page_numbers.append("...")

    # Add the last page.
    if page_max > current_page:
        page_numbers.append(page_max)

    def url_for(page):
        query = request.params.dict_of_lists()
        query["page"] = page
        return request.current_route_path(_query=query)

    return {
        "cur": current_page,
        "max": page_max,
        "next": next_,
        "numbers": page_numbers,
        "prev": prev,
        "url_for": url_for,
    }


@view_defaults(
    route_name="account_user_event",
    renderer="h:templates/accounts/kmass-user-event.html.jinja2",
    is_authenticated=True,
)
class UserEventSearchController:
    """View callables for the "activity.search" route."""

    def __init__(self, request):
        self.request = request

    @view_config(request_method="GET")
    def get(self):  # pragma: no cover

        # page
        page = self.request.params.get("page", 1)

        try:
            page = int(page)
        except ValueError:
            page = 1

        # Don't allow negative page numbers.
        page = max(page, 1)

        page_size = self.request.params.get("pageSize", PAGE_SIZE)
        if page_size == "all":
            pass
        else:
            try:
                page_size = int(page_size)
            except ValueError:
                page_size = PAGE_SIZE

        sortby = self.request.params.get("sortby", SORT_BY)
        order = self.request.params.get("order", ORDER)

        # Fetch results.
        if type(page_size) == int:
            limit = page_size
            offset = (page - 1) * page_size
            fetch_result = fetch_user_event(userid=self.request.authenticated_userid, offset=offset, limit=limit, sortby="-"+sortby if order =="desc" else sortby)
        else:
            fetch_result = fetch_all_user_event(userid=self.request.authenticated_userid, sortby="-"+sortby if order =="desc" else sortby)

        table_results = fetch_result["table_result"]
        total = fetch_result["total"]
        table_head = list(table_results[0].keys()) if table_results else []

        properties = get_user_event_fields()
        values=[]
        for key in properties:
            values.append((key, properties[key]["title"]))

        def max_display(word, length):
            if type(word) is str and len(word) > length:
                return word[:length] + "..."
            else:
                return word

        return {
            "table_head": table_head,
            "table_results": table_results,
            "page": paginate(self.request, total, page_size=page_size) if type(page_size) == int else paginate(self.request, total, page_size=total),
            "values": values,
            "query": {
                "page": page,
                "page_size": page_size,
                "sortby": sortby,
                "order": order,
            },
            "max_display": max_display,
        }

    @view_config(request_method="POST")
    def post(self):
        userid = self.request.authenticated_userid
        try:
            name = util.user.split_user(userid)["username"]
        except InvalidUserId:
            name = userid

        sortby = self.request.params.get("sortby", SORT_BY)
        order = self.request.params.get("order", ORDER)

        bunch_data = fetch_all_user_event(userid=userid, sortby="-"+sortby if order =="desc" else sortby)['table_result']

        csv_data = StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(bunch_data[0].keys())
        for item in bunch_data:
            csv_writer.writerow(item.values())

        res = response.Response(content_type='text/csv')
        res.content_disposition = f'attachment; filename="{name}_result.csv"'
        res.body = csv_data.getvalue().encode('utf-8')
        return res