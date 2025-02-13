"""Activity pages views."""

import csv
import math
from io import StringIO

from pyramid import response
from pyramid.httpexceptions import HTTPBadRequest, HTTPFound
from pyramid.view import view_config, view_defaults

from h import util
from h.exceptions import InvalidUserId
from h.i18n import TranslationString as _

START_PAGE = 1
PAGES = 5
DEFAULT_PAGE_SIZE = 1000
PAGE_SIZE = 25
SORT_BY = "timestamp"
ORDER = "desc"
MAX_LIMIT = DEFAULT_PAGE_SIZE * 10

PAGE_SIZE_LIST = ["10", "25", "50", "100"]
ORDER_LIST = ["desc", "asc"]

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
    def get(self):
        start_page = self.request.params.get('page', START_PAGE)
        pages = self.request.params.get('pages', PAGES)
        page_size = self.request.params.get('pageSize', PAGE_SIZE)
        sortby = self.request.params.get('sortby', SORT_BY)
        order = self.request.params.get('order', ORDER)

        params = {
            "page": start_page,
            "pages": pages,
            "pageSize": page_size,
            "sortby": sortby,
            "order" : order,
        }
        return HTTPFound(
            location=self.request.route_path(
                "account_user_event", _query=params
            )
        )

    @view_config(
        request_method="GET",
        request_param=["page", "pages", "pageSize", "sortby", "order"],
    )
    def get_param(self):  # pragma: no cover
        trace_service = self.request.find_service(name="trace")

        # page
        page = self.request.params.get("page")
        pages = self.request.params.get("pages")
        page_size = self.request.params.get("pageSize")
        sortby = self.request.params.get("sortby")
        order = self.request.params.get("order")
        params = {
            "page": page,
            "pages": pages,
            "pageSize": page_size,
            "sortby": sortby,
            "order" : order,
        }

        if page_size not in PAGE_SIZE_LIST:
            params["pageSize"] = PAGE_SIZE_LIST[1]
            return HTTPFound(
                location=self.request.route_path(
                    "account_user_event", _query=params
                )
            )

        total = trace_service.count(self.request.authenticated_userid)
        pg = paginate(self.request, total, page_size=int(page_size))

        try:
            page = int(page)
        except ValueError:
            params["page"] = START_PAGE
            return HTTPFound(
                location=self.request.route_path(
                    "account_user_event", _query=params
                )
            )

        if page > pg["max"] or page < 0:
            params["page"] = START_PAGE
            return HTTPFound(
                location=self.request.route_path(
                    "account_user_event", _query=params
                )
            )

        properties = trace_service.get_user_event_sortable_fields()
        keys=[]
        for key in properties:
            keys.append(key)

        if sortby not in keys:
            params["sortby"] = SORT_BY
            return HTTPFound(
                location=self.request.route_path(
                    "account_user_event", _query=params
                )
            )

        if order not in ORDER_LIST:
            params["order"] = ORDER_LIST[0]
            # location = f"{base_url}/account/user-event?{urlencode(params)}"
            # return HTTPFound(location=location)
            return HTTPFound(
                location=self.request.route_path(
                    "account_user_event", _query=params
                )
            )

        # Fetch results.
        limit = int(page_size)
        offset = (page - 1) * int(page_size)
        table_results = trace_service.user_event_search_query(
            userid = self.request.authenticated_userid,
            offset = offset,
            limit = limit,
            sortby = "-" + sortby if order =="desc" else sortby
        )

        table_head = list(table_results[0].keys()) if table_results else []

        properties = trace_service.get_user_event_sortable_fields()
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
            "page": pg,
            "values": values,
            "page_size_option": PAGE_SIZE_LIST,
            "order_option": ORDER_LIST,
            "query": {
                "page": str(page),
                "pages": pages,
                "page_size": page_size,
                "sortby": sortby,
                "order": order,
                "link": self.request.route_path("account_user_event", _query=params)
            },
            "max_display": max_display,
        }

    @view_config(request_method="POST")
    def post(self):
        trace_service = self.request.find_service(name="trace")

        userid = self.request.authenticated_userid
        try:
            username = util.user.split_user(userid)["username"]
        except InvalidUserId:
            return HTTPFound(self.request.route_path("login"))
        except Exception as e:
            return HTTPFound(self.request.route_path("index"))

        page = self.request.POST.get("page")
        pages = self.request.POST.get("pages")
        page_size = self.request.POST.get("pageSize")
        sortby = self.request.POST.get("sortby")
        order = self.request.POST.get("order")

        if page_size not in PAGE_SIZE_LIST:
            raise HTTPBadRequest("Invalid page size value")

        total = trace_service.count(self.request.authenticated_userid)
        pg = paginate(self.request, total, page_size=int(page_size))

        try:
            page = int(page)
        except ValueError:
            raise HTTPBadRequest("The page value is illegal")

        if page > pg["max"] or page < 0:
            raise HTTPBadRequest("The page value is either too large or too small")

        try:
            pages = int(pages)
        except ValueError:
            raise HTTPBadRequest("The value of pages is illegal")

        if pages > pg["max"] or pages < 0:
            raise HTTPBadRequest("The value of pages is either too large or too small")

        properties = trace_service.get_user_event_sortable_fields()
        keys=[]
        for key in properties:
            keys.append(key)

        if sortby not in keys:
            raise HTTPBadRequest("The sortby value is illegal")

        if order not in ORDER_LIST:
            raise HTTPBadRequest("The order value is illegal")

        limit = int(page_size) * pages
        offset = (page - 1) * int(page_size)

        if limit > MAX_LIMIT:
            raise HTTPBadRequest("The value of page is out of range")

        bunch_data = trace_service.user_event_search_query(
            userid = self.request.authenticated_userid,
            offset = offset,
            limit = limit,
            sortby = "-" + sortby if order =="desc" else sortby
        )

        csv_data = StringIO()
        csv_writer = csv.writer(csv_data)
        csv_writer.writerow(bunch_data[0].keys())
        for item in bunch_data:
            csv_writer.writerow(item.values())

        res = response.Response(content_type='text/csv')
        res.body = csv_data.getvalue().encode('utf-8')
        res.headers["Content-Disposition"] = f'attachment; filename="{username}_result.csv"'

        return res
