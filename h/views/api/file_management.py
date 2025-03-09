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
import uuid
import os
from pyramid import i18n
from pyramid import httpexceptions

from h.security import Permission
from h.traversal import FileManagementContext
from h.views.api.config import api_config
from h.views.api.exceptions import PayloadError


_ = i18n.TranslationStringFactory(__package__)


def check_dir_exist(path):
    if os.path.exists(path):
        return True
    try:
        os.mkdir(path)
    except FileExistsError as e:
        return True
    except FileNotFoundError as e:
        return False
    except Exception as e:
        return False
    else:
        if os.path.exists(path):
            return True
        else:
            return False


@api_config(
    versions=["v1", "v2"],
    route_name="api.upload",
    request_method="POST",
    permission=Permission.Profile.UPDATE,
    link_name="upload",
    description="Upload files to the cloud",
)
def upload(request):
    """Retrieve the traces for this request's user event record."""
    # validate input POST
    filename = request.POST.get('name')
    input_file = request.POST.get('file').file
    size = request.POST.get('size')
    file_type = request.POST.get('type')
    path = request.POST.get('path')

    if not filename or not size or not file_type or not path:
        return httpexceptions.HTTPBadRequest()

    if input_file is None:
        return httpexceptions.HTTPBadRequest()

    settings = request.registry.settings
    user_root_url = settings.get("user_root_url")
    user_root = settings.get("user_root")
    userid = request.authenticated_userid

    file_management = request.find_service(name="file_management")
    # create parent directories
    if dir_meta := file_management.check_v_dir_exist(path):
        v_dir = dir_meta.file_path
    else:
        v_dir = file_management.mk_v_dir(
            path,
            {
                "userid" : userid,
                "link" : os.path.join(user_root, path),
                "access_permissions": "private",
            }
        )

    name = uuid.uuid4()
    file_type = file_management.check_accpectable_file_type(file_type)
    if not file_type:
        return httpexceptions.HTTPUnsupportedMediaType()

    full_filename = os.path.join('%s.%s'%(name, file_type))
    actual_save_path = os.path.join(user_root, file_type)
    relpath = os.path.join(file_type, '%s.%s'%(name, file_type))

    file_full_path = os.path.join(actual_save_path, full_filename)
    url = os.path.join(user_root_url, "static", relpath)
    now = datetime.datetime.now().timestamp()

    if check_dir_exist(actual_save_path):
        file = file_management.save_file(
            input_file,
            file_full_path,
            {
                "filename": filename,
                "file_id" : str(name),
                "create_stamp" : now,
                "file_type" : file_type,
                "file_path" : v_dir,
                "link" : file_full_path,
                "userid" : userid,
                "url" : url,
            }
        )
        if file:
            return file_management.file_meta_dict(file)

    return httpexceptions.HTTPConflict()


@api_config(
    versions=["v1", "v2"],
    route_name="api.trees",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
    link_name="trees.read",
    description="List all files of the user",
)
def trees(request):
    userid = request.authenticated_userid
    dir = request.params.get('dir')
    file_management = request.find_service(name="file_management")

    [files, dir] = file_management.get_user_files_list_by_dir(userid, dir)
    return {
        "dir": dir,
        "files": files,
    }


@api_config(
    versions=["v1", "v2"],
    route_name="api.tree",
    request_method="GET",
    permission=Permission.Profile.UPDATE,
    link_name="tree.read",
    description="Fetch a file",
)
def read(context: FileManagementContext, request):
    filemeta = context.filemeta
    file_management = request.find_service(name="file_management")
    return file_management.file_meta_dict(filemeta)


@api_config(
    versions=["v1", "v2"],
    route_name="api.tree",
    request_method=("PATCH", "PUT"),
    permission=Permission.Profile.UPDATE,
    link_name="tree.update",
    description="Update file status",
)
def update(context: FileManagementContext, request):
    userid = request.authenticated_userid
    data = _json_payload(request)
    filemeta = context.filemeta

    file_management = request.find_service(name="file_management")

    update = {}
    permission = data.get("permission", None)
    if permission:
        update["access_permissions"] = permission

    result = file_management.update_file_meta(filemeta.pk, update, userid)

    return file_management.file_meta_dict(result)


@api_config(
    versions=["v1", "v2"],
    route_name="api.tree",
    request_method="DELETE",
    permission=Permission.Profile.UPDATE,
    link_name="tree.delete",
    description="Delete a file",
)
def delete(context: FileManagementContext, request):
    file_meta = context.filemeta
    userid = request.authenticated_userid

    file_management = request.find_service(name="file_management")
    succ = file_management.delete_file_meta(file_meta.pk, userid)
    if succ:
        return {"id": context.id, "deleted": succ}
    else:
        return httpexceptions.HTTPUnauthorized()


def _json_payload(request):
    """
    Return a parsed JSON payload for the request.

    :raises PayloadError: if the body has no valid JSON body
    """
    try:
        return request.json_body
    except ValueError as err:
        raise PayloadError() from err
