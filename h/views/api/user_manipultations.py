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
import json
import os
import re
import requests
import shutil
from redis_om import get_redis_connection
from urllib.parse import urljoin

from h.exceptions import InvalidUserId
from h.security import Permission
from h.views.api.config import api_config

def split_user(userid):
    """
    Return the user and domain parts from the given user id as a dict.

    For example if userid is u'acct:seanh@hypothes.is' then return
    {'username': u'seanh', 'domain': u'hypothes.is'}'

    :raises InvalidUserId: if the given userid isn't a valid userid

    """
    match = re.match(r"^acct:([^@]+)@(.*)$", userid)
    if match:
        return {"username": match.groups()[0], "domain": match.groups()[1]}
    raise InvalidUserId(userid)


@api_config(
    versions=["v1", "v2"],
    route_name="api.upload",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="upload",
    description="Upload files to the cloud",
)
def upload(request):
    username = split_user(request.authenticated_userid)["username"]
    settings = request.registry.settings

    if request.POST["file-upload"] is None:
        return {"error": "no file"}
    
    fullname = None # request.POST['file-upload'].filename
    input_file = request.POST["file-upload"].file

    meta = request.POST["meta"]

    if meta:
        lnk = json.loads(meta)["link"]
        for item in lnk:
            url = item["href"]
            domain = re.search(r"(?P<url>https?://[^\s]+)", url)
            if domain:
                domain = domain.group("url").split("?")[0]
                # pdf
                if domain.endswith(".pdf"):
                    fullname = domain.split("/")[-1]
                else:
                    fullname = re.search(r"(?P<domain>https?://)(?P<host>[^/:]+)", domain).group("host") + ".html"

        name = json.loads(meta)["title"]
        if name != "" and "/" not in name:
            fullname = name
    file_type_with_dot = os.path.splitext(fullname)[1]
    try:
        # check the user directory
        dir = os.path.join(settings.get("user_root"), username)
        if not os.path.exists(dir):
            os.mkdir(dir)

        # create the file
        file_path = os.path.join(dir, fullname)

        with open(file_path, "wb") as output_file:
            shutil.copyfileobj(input_file, output_file)
    except Exception as e:
        return {"error": repr(e)}

    # transfer to TA B
    url = urljoin(request.registry.settings.get("query_url"), "upload")
    files = {"myFile": (fullname, input_file)}
    response = requests.post(url, files=files)
    return response


@api_config(
    versions=["v1", "v2"],
    route_name="api.delete",
    request_method="DELETE",
    permission=Permission.Annotation.CREATE,
    link_name="delete",
    description="Delete files to the cloud",
)
def delete(request):
    username = split_user(request.authenticated_userid)["username"]
    settings = request.registry.settings

    file_path = request.GET.get('file')

    try:
        # check the user directory
        # dir = os.path.join(settings.get("user_root"), username, file_name)

        if not os.path.exists(file_path):
            return {'error': 'could not find the file in user repository'}
        else:
            os.remove(file_path)
            return {'succ': file_path + ' has been removed successfully'}
    except Exception as e:
        return {"error": repr(e)}


def iterate_directory(dir, name, url):
    directory_node = {
        'path': dir,
        'id': dir,
        'name': name,
        'type': 'dir', # dir | file
        'link': os.path.join(url, name),
        'children': []
    }
    with os.scandir(dir) as it:
        for entry in it:
            if entry.is_file():
                file_node = {
                    'path': os.path.join(dir, entry.name),
                    'id': dir,
                    'name': entry.name,
                    'type': 'file',
                    'link': os.path.join(url, entry.name),
                    'children': []
                }
                directory_node['children'].append(file_node)
            elif entry.is_dir():
                directory_node['children'].append(iterate_directory(os.path.join(dir, entry.name), entry.name, url))

    return directory_node


@api_config(
    versions=["v1", "v2"],
    route_name="api.repository",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
    link_name="repository",
    description="Get user cloud repository",
)
def repository(request):
    username = split_user(request.authenticated_userid)["username"]
    settings = request.registry.settings
    url = os.path.join(settings.get("user_root_url"), "static", username)

    dir = os.path.join(settings.get("user_root"), username)
    if not os.path.exists(dir):
            os.mkdir(dir)
    return iterate_directory(dir, settings.get("user_root"), url)


@api_config(
    versions=["v1", "v2"],
    route_name="api.client_url",
    request_method="GET",
    link_name="client",
    description="Get the Client location",
)
def client_url(request):
    return {
        "base_url": request.registry.settings.get("homepage_url"),
        "url_string": "",
    }


@api_config(
    versions=["v1", "v2"],
    route_name="api.recommendation",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="push_recommendation",
    description="Post the Recommendation",
)
def push_recommendation(request):
    username = split_user(request.authenticated_userid)["username"]
    data = request.json_body

    key = "h:Recommendation:" + username + ":" + data["url"]
    get_redis_connection().set(key, json.dumps(data))

    expiration_time = 120
    get_redis_connection().expire(key, expiration_time)

    return {
        "succ": data["url"] + "has been saved"
    }


@api_config(
    versions=["v1", "v2"],
    route_name="api.recommendation",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
    link_name="pull_recommendation",
    description="Get the Recommendation",
)
def pull_recommendation(request):
    username = split_user(request.authenticated_userid)["username"]
    encoded_url = request.GET.get("url")

    key_pattern = "h:Recommendation:" + username + ":" + encoded_url
    keys = get_redis_connection().keys(key_pattern)

    if len(keys) > 0:
        ret = get_redis_connection().getdel(keys[0])
        print("ret", ret)
        return json.loads(ret)

    return {
        "id": "",
        "url": "",
        "type": "",
        "title": "",
        "context": "",
    }
