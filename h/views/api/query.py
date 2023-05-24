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
import requests
from redis_om.model import NotFoundError

from h.security import Permission
from h.views.api.config import api_config
from h.models_redis import Result, Bookmark, UserRole


@api_config(
    versions=["v1", "v2"],
    route_name="api.query",
    link_name="query",
    description="Querying",
)
def query(request):
    user_role = request.user_role
    query = request.GET.get("q")
    url = request.registry.settings.get("query_url")

    params = {
        'q': query
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        json_data = response.json()

        count = 0
        for topic in json_data["context"]:
            rcount = 0
            for result_item in topic:
                meta = result_item["metadata"]
                if "title" in meta and "url" in meta:
                    # find out the response result if it was existing
                    existing_results = Result.find(
                        Result.title == meta["title"]
                        # (Result.title == meta["title"]) &
                        # (Result.url == meta["url"])
                    ).all()
                    # find out the result was bookmarked
                    if len(existing_results):
                        result_pk = existing_results[0].pk
                        result_item["id"] = result_pk
                        if user_role:
                            bookmarks = Bookmark.find(
                                (Bookmark.result == result_pk) &
                                (Bookmark.user.pk == user_role.pk)
                            ).all()
                            if len(bookmarks):
                                if not bookmarks[0].deleted:
                                    result_item["is_bookmark"] = True
                    else:
                        # else insert new response result
                        result = Result(**meta)
                        result_item["id"] = result.pk
                        result.save()
                else:
                    if "title" not in meta:
                        meta["title"] = "missing title"
                    if "url" not in meta:
                        meta["title"] = meta["title"] + " and URL"
                rcount += 1
            count += 1

        return json_data
    else:
        return {
            'status' : "proxy reverse can't get the response, status code: " + str(response.status_code),
            'query' : query,
            'context' : []
        }


@api_config(
    versions=["v1", "v2"],
    route_name="api.bookmark",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="bookmark",
    description="Bookmark",
)
def bookmark(request):
    user_role = request.user_role

    # id            : str
    # query         : str
    # is_bookmark   : boolean
    data = request.json_body
    result_id = data["id"]

    try:
        Result.get(result_id)
    except NotFoundError:
        return {"error" : "no corresponding result"}

    query = data["query"]

    data["result"] = result_id
    data["user"] = user_role
    data["deleted"] = 1 - int(data["is_bookmark"])
    data.pop("is_bookmark")
    data.pop("id")
    bookmark = None

    try:
        exist_bookmarks = Bookmark.find(
            (Bookmark.result == result_id) &
            (Bookmark.user.pk == user_role.pk) &
            (Bookmark.query == query)
        ).all()
        if len(exist_bookmarks) == 1:
            bookmark = exist_bookmarks[0]
            bookmark.deleted = data["deleted"]
        elif len(exist_bookmarks) > 1:
            return {"error": "multiple bookmark error"}
        else:
            bookmark = Bookmark(**data)
        bookmark.save()

    except Exception as e:
        return {"server error": repr(e)}
    else:
        return {
            "succ": "bookmark" + bookmark.pk + "has been saved"
        }


@api_config(
    versions=["v1", "v2"],
    route_name="api.typing",
    request_method="GET",
    link_name="typing",
    description="Get the typing word and return suggestion",
)
def typing(request):
    word = request.GET.get('q')

    if not word:
        return []

    matched_bookmarks = Bookmark.find(Bookmark.query % word).all()
    result = []
    for index, bookmark in enumerate(matched_bookmarks):
        result.append({"id": index, "text": bookmark.query})

    return result
