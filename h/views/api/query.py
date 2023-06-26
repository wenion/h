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
import datetime
import os
import requests
import distance
from redis_om.model import NotFoundError
from urllib.parse import urljoin

from h.security import Permission
from h.views.api.config import api_config
from h.models_redis import Result, Bookmark, UserRole, UserEvent, create_user_event, save_in_redis


def create_user_event(event_type, tag_name, text_content, base_url, userid):
    return {
        "event_type": event_type,
        "timestamp": int(datetime.datetime.now().timestamp() * 1000),
        "tag_name": tag_name,
        "text_content": text_content,
        "base_url": base_url,
        "userid": userid
    }


@api_config(
    versions=["v1", "v2"],
    route_name="api.query",
    link_name="query",
    description="Querying",
)
def query(request):
    user_role = request.user_role
    userid = "unknown user"
    if user_role:
        userid = user_role.userid

    query = request.GET.get("q")
    url = urljoin(request.registry.settings.get("query_url"), "query")

    params = {
        'q': query
    }
    query_request = create_user_event("server-record", "QUERY REQUEST", query, request.url, userid)
    save_in_redis(query_request)
    response = requests.get(url, params=params)
    query_response = create_user_event("server-record", "QUERY RESPONSE", query, request.url, userid)
    save_in_redis(query_response)

    if response.status_code == 200:
        json_data = response.json()

        count = 0
        for topic in json_data["context"]:
            rcount = 0
            for result_item in topic:
                meta = result_item["metadata"]
                if "title" in meta and "url" in meta:
                    prefix = "/home/ubuntu/KMASS-monash/DSI/Neural-Corpus-Indexer-NCI-main/Data_KMASS/all_data"
                    origin_url = meta["url"]
                    # special address
                    # uploaded pdf files and system pdf files will not provide url
                    # we need to complete for them
                    if "http://" not in origin_url and "https://" not in origin_url:
                        if prefix in origin_url:
                            # user upload pdf
                            relpath = os.path.join("static", os.path.relpath(origin_url, prefix))
                            meta["url"] = urljoin(request.registry.settings.get("user_root_url"), relpath)
                        else:
                            # system pdf file
                            relpath = os.path.join("static", origin_url)
                            meta["url"] = urljoin("https://colam.kmass.cloud.edu.au", relpath)

                    # find out the response result if it was existing
                    existing_results = Result.find(
                        Result.title == meta["title"]
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
                elif "title" not in meta and "url" not in meta:
                    meta["title"] = "The title and URL are missing."
                elif "title" not in meta and "url" in meta:
                    meta["title"] = "The title is missing."
                elif "title" in meta and "url" not in meta:
                    meta["title"] = "The URL is missing."
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


def get_user_profile_similarity(user_role_1, user_role_2):
    value = 0
    if user_role_1.faculty == user_role_2.faculty:
        value += 1
    if user_role_1.teaching_role == user_role_2.teaching_role:
        value += 1
    if user_role_1.teaching_unit == user_role_2.teaching_unit:
        value += 1
    if user_role_1.years_of_experience < 3:
        user_role_1.years_of_experience = 1
    elif user_role_1.years_of_experience > 10:
        user_role_1.years_of_experience = 3
    else:
        user_role_1.years_of_experience = 2
    if user_role_2.years_of_experience < 3:
        user_role_2.years_of_experience = 1
    elif user_role_2.years_of_experience > 10:
        user_role_2.years_of_experience = 3
    else:
        user_role_2.years_of_experience = 2
    if user_role_1.years_of_experience == user_role_2.years_of_experience:
        value += 1
    # print("get_user_profile_similarity", value / 4)
    return value / 4


@api_config(
    versions=["v1", "v2"],
    route_name="api.typing",
    request_method="GET",
    link_name="typing",
    description="Get the typing word and return suggestion",
)
def typing(request):
    user_role = request.user_role
    word = request.GET.get('q')

    if not word:
        return []

    matched_bookmarks = Bookmark.find(
        Bookmark.user.expert == 1
    ).all()
    result = []
    seen_texts = set()
    for index, bookmark in enumerate(matched_bookmarks):
        if user_role:
            value = get_user_profile_similarity(bookmark.user, user_role)
        else:
            value = 0
        value = value* 0.33 + (1 - distance.nlevenshtein(word, bookmark.query, method=2))*0.5

        if bookmark.query not in seen_texts:
            result.append({"text": bookmark.query, "value": value})
            seen_texts.add(bookmark.query)

    sorted_dict = sorted(result, key=lambda x: x["value"], reverse=True)
    # print("sorted_dict", sorted_dict, "\n")

    return sorted_dict[:5]
