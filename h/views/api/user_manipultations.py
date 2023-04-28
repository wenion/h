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
import shutil

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

    if request.POST['file-upload'] is None:
        return {"error": "no file"}
    
    fullname = request.POST['file-upload'].filename
    input_file = request.POST['file-upload'].file

    meta = request.POST['meta']

    if meta:
        lnk = json.loads(meta)['link']
        for item in lnk:
            url = item['href']
            domain = re.search(r"(?P<url>https?://[^\s]+)", url)
            if domain:
                domain = domain.group("url").split('?')[0]
                # pdf
                if domain.endswith('.pdf'):
                    fullname = domain.split('/')[-1]
                else:
                    fullname = re.search(r"(?P<domain>https?://)(?P<host>[^/:]+)", domain).group("host") + '.html'

    try:
        # check the user directory
        dir = os.path.join(settings.get("user_root"), username)
        if not os.path.exists(dir):
            os.mkdir(dir)

        # create the file
        file_path = os.path.join(dir, fullname)

        with open(file_path, 'wb') as output_file:
            shutil.copyfileobj(input_file, output_file)
    except Exception as e:
        return {"error": e}

    return {"succ": fullname + "has been saved"}


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

    try:
        # check the user directory
        dir = os.path.join(settings.get("user_root"), username)
        if not os.path.exists(dir):
            os.mkdir(dir)
            return {
                'current_path' : dir,
                'current_dir' : []
            }

        current_dir = []
        with os.scandir(dir) as it:
            for entry in it:
                type = 'dir'
                if entry.is_file():
                    type = 'file'
                elif entry.is_symlink():
                    type = 'symlink'
                item = {'name' : entry.name, 'path' : entry.path, 'type' : type}
                current_dir.append(item)
        return {
            'current_path' : dir,
            'current_dir' : current_dir
        }

    except Exception as e:
        return {
            'current_path' : 'error occurs, could not access the repository',
            'current_dir' : []
            }