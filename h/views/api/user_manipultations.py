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
import copy
from datetime import datetime, date, timedelta
import json
import os
import openai
import re
import requests
import shutil
from redis_om import get_redis_connection
from urllib.parse import urljoin, urlparse, unquote

from h.exceptions import InvalidUserId
from h.security import Permission
from h.views.api.config import api_config
from h.models_redis import UserEvent, Rating
from h.models_redis import get_highlights_from_openai, create_user_event, save_in_redis, add_user_event
from h.services import OrganisationEventPushLogService

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
    # is public file or not?
    # need to be ingested or not?
    # source: google? repository? html?
    userid = request.authenticated_userid
    username = split_user(userid)["username"]
    settings = request.registry.settings

    if request.POST["file-upload"] is None:
        return {"error": "no file"}

    root_dir = os.path.join(settings.get("user_root"), username)
    public_pdf_dir = os.path.join(settings.get("user_root"), "new-pdf")
    input_file = request.POST["file-upload"].file

    meta = json.loads(request.POST["meta"])
    filetype = meta["type"]

    if not os.path.exists(root_dir):
        os.mkdir(root_dir)

    if filetype == "html":
        print("meta", meta)
        parsed_url = urlparse(meta["link"])
        host_name = parsed_url.netloc
        name = meta["name"]
        if name == "":
            name = host_name + parsed_url.path.split("/")[-1]
        if not name.endswith(".html"):
            name = name + ".html"
        try:
            upload_request = create_user_event("server-record", "UPLOAD REQUEST", name, request.url, userid)
            save_in_redis(upload_request)
            filepath = os.path.join(root_dir, name)
            if os.path.exists(filepath):
                upload_response = create_user_event("server-record", "UPLOAD RESPONSE FAILED", name + " already exists", request.url, userid)
                save_in_redis(upload_response)
                return {"error": name + " already exists"}
            with open(filepath, "wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
        except Exception as e:
            upload_response = create_user_event("server-record", "UPLOAD RESPONSE FAILED", name + "error:" + repr(e), request.url, userid)
            save_in_redis(upload_response)
            return {"error": repr(e)}

        relavtive_path = os.path.relpath(filepath, settings.get("user_root"))
        upload_response = create_user_event("server-record", "UPLOAD RESPONSE SUCC", name, request.url, userid)
        save_in_redis(upload_response)
        return {"succ": {
            "depth": 0,
            "id": root_dir,
            "link": os.path.join(settings.get("user_root_url"), "static", relavtive_path),
            "name": name,
            "path": filepath,
            "type": "file"
        }}

    if filetype == "google":
        name = meta["name"]
        filepath = os.path.join(root_dir, name)
        relavtive_path = os.path.relpath(filepath, settings.get("user_root"))
        print("google filepath", filepath)
        if os.path.exists(filepath):
            return {"error": name + " already exists"}
        try:
            with open(filepath, "wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
        except Exception as e:
            return {"error": repr(e)}
        else:
            return {"succ": {
                "depth": 0,
                "id": root_dir,
                "link": os.path.join(settings.get("user_root_url"), "static", relavtive_path),
                "name": name,
                "path": filepath,
                "type": "file"
            }}

    parent_path = meta["id"]
    file_path = meta["path"]
    depth = int(meta["depth"])
    name = meta["name"]
    if file_path == "" or name == "":
        upload_request = create_user_event("server-record", "UPLOAD FAILED", name, request.url, userid)
        save_in_redis(upload_request)
        return {
            "error": str(meta)
        }

    relavtive_path = os.path.relpath(file_path, settings.get("user_root"))
    print("filepath", file_path)

    if not os.path.exists(root_dir):
        os.mkdir(root_dir)

    if not os.path.exists(public_pdf_dir):
        os.mkdir(public_pdf_dir)

    public_file_path = os.path.join(public_pdf_dir, name)
    try:
        upload_request = create_user_event("server-record", "UPLOAD REQUEST", name, request.url, userid)
        save_in_redis(upload_request)
        # check the user directory
        if not os.path.exists(parent_path):
            os.mkdir(parent_path)

        if os.path.exists(file_path):
            upload_response = create_user_event("server-record", "UPLOAD RESPONSE FAILED", name + " already exists", request.url, userid)
            save_in_redis(upload_response)
            return {"error": name + " already exists"}

        with open(file_path, "wb") as output_file:
            shutil.copyfileobj(input_file, output_file)
        with open(file_path, "rb") as source_file:
            with open(public_file_path, "wb") as output_file:
                shutil.copyfileobj(source_file, output_file)
    except Exception as e:
        upload_response = create_user_event("server-record", "UPLOAD RESPONSE FAILED", name + "error:"+ repr(e), request.url, userid)
        save_in_redis(upload_response)
        return {"error": repr(e)}

    upload_response = create_user_event("server-record", "UPLOAD RESPONSE SUCC", name, request.url, userid)
    save_in_redis(upload_response)

    # transfer to TA B
    local_file = open(file_path, "rb")
    files = {"myFile": (name, local_file)}
    url = urljoin(request.registry.settings.get("query_url"), "upload")
    data = {"url": os.path.join(settings.get("user_root_url"), "static", relavtive_path)}

    succ_response = {"succ": {
        "depth": depth,
        "id": parent_path,
        "link": os.path.join(settings.get("user_root_url"), "static", relavtive_path),
        "name": name,
        "path": file_path,
        "type": "file"
    }}

    try:
        # start ingest
        ingest_request = create_user_event("server-record", "INGEST REQUEST", name, url, userid)
        save_in_redis(ingest_request)
        response = requests.post(url, files=files, data=data)
        # result = response.json()
    except Exception as e:
        ingest_response = create_user_event("server-record", "INGEST RESPONSE FAILED", name +" error:"+ repr(e), url, userid)
        save_in_redis(ingest_response)
        return {"error": repr(e)}
    else:
        if response.status_code != 200:
            ingest_response = create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:TA B proxy error", url, userid)
            save_in_redis(ingest_response)
            return {"error": "TA B proxy error"}
    try:
        result = response.json()
    except Exception as e:
        ingest_response = create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:" + repr(e), url, userid)
        save_in_redis(ingest_response)
        return {"error": repr(e)}
    else:
        # check the ingesting is succ?
        # if "error" in result:
        #     if "[the ingestion failed]" in result["error"]:
        #         succ_response["tab"] = result["error"]
        #     else:
        #         return result
        if result["status"] == 404:
            ingest_response = create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:" + result["message"], url, userid)
            save_in_redis(ingest_response)
            return {"error": result["message"]}
        elif result["status"] == 303:
            ingest_response = create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:303 " + result["message"], url, userid)
            save_in_redis(ingest_response)
            pass
        elif result["status"] == 304:
            ingest_response = create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:304 " + result["message"], url, userid)
            save_in_redis(ingest_response)
        elif result["status"] == 200:
            ingest_response = create_user_event("server-record", "INGEST RESPONSE SUCC", name, url, userid)
            save_in_redis(ingest_response)


    local_file.close()
    return succ_response


@api_config(
    versions=["v1", "v2"],
    route_name="api.delete",
    request_method="DELETE",
    permission=Permission.Annotation.CREATE,
    link_name="delete",
    description="Delete files from the cloud",
)
def delete(request):
    userid = request.authenticated_userid
    settings = request.registry.settings

    file_path = request.GET.get('file')
    filename = os.path.basename(file_path)
    base_name, extension = os.path.splitext(filename)
    public_pdf_dir = os.path.join(settings.get("user_root"), "new-pdf")
    public_file_path = os.path.join(public_pdf_dir, filename)

    try:
        delete_request = create_user_event("server-record", "DELETE", filename, request.url, userid)
        save_in_redis(delete_request)
        print("file_path", file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        print("public_file_path", public_file_path)
        if os.path.exists(public_file_path):
            os.remove(public_file_path)
    except Exception as e:
        return {"error": repr(e)}

    # try:
    #     url = urljoin(request.registry.settings.get("query_url"), "delete")
    #     data = {"filename": filename, "filetype": extension}
    #     response = requests.post(url, data=data)
    # except Exception as e:
    #     return {"error": repr(e)}
    # else:
    #     if response.status_code != 200:
    #         return {"error": "TA B proxy error"}

    # try:
    #     result = response.json()
    # except Exception as e:
    #     return {"error": repr(e)}
    # else:
    #     # check the ingesting is succ?
    #     if "error" in result:
    #         return result

    return {'succ': {
        "filepath": file_path,
        "parent_filepath": os.path.dirname(file_path),
        }}


def iterate_directory(dir, name, url, depth):
    current_path = os.path.join(url, name)
    directory_node = {
        'path': dir,
        'id': dir,
        'name': name,
        'type': 'dir', # dir | file
        'link': current_path,
        'children': [],
        'depth': depth,
    }
    with os.scandir(dir) as it:
        for entry in it:
            if entry.is_file():
                file_node = {
                    'path': os.path.join(dir, entry.name),
                    'id': dir,
                    'name': entry.name,
                    'type': 'file',
                    'link': os.path.join(current_path, entry.name),
                    'children': [],
                    'depth': depth,
                }
                directory_node['children'].append(file_node)
            elif entry.is_dir():
                directory_node['children'].append(iterate_directory(os.path.join(dir, entry.name), entry.name, current_path, depth + 1))

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
    return iterate_directory(dir, username, os.path.join(settings.get("user_root_url"), "static"), 0)


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
    data = request.json_body # dict

    if data["query"] and data["context"] and data["query"] != "":
        # data["context"].replace("\n", " ")
        value = get_highlights_from_openai(data["query"], data["context"])
        if "succ" in value:
            data["context"] = value["succ"]
        else:
            data["context"] = "error: " + value["error"]

    # key = "h:Recommendation:" + username + ":" + data["url"]
    # get_redis_connection().set(key, json.dumps(data))

    # expiration_time = 120
    # get_redis_connection().expire(key, expiration_time)
    request.find_service(name="highlight_event").create(username, data['url'], json.dumps(data))

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
    userid = request.authenticated_userid
    username = split_user(userid)["username"]
    encoded_url = request.GET.get("url")
    url = ""
    if encoded_url:
        url = unquote(encoded_url)
    redis_ret = {
        "id": "",
        "url": "",
        "type": "",
        "title": "",
        "context": "",
    }
    rating = {
        "timestamp": 0,
        "relevance": "",
        "base_url": url,
        "timeliness": "",
    }

    # from redis
    # key_pattern = "h:Recommendation:" + username + ":" + url
    # key_pattern = "h:Recommendation:" + username + ":*"
    # keys = get_redis_connection().keys(key_pattern)

    # if len(keys) > 0:
    #     value = get_redis_connection().get(keys[0]) # type json
    #     redis_ret.update(json.loads(value))

    value = request.find_service(name="highlight_event").get_by_username_and_url(username, url)
    if value:
        redis_ret.update(json.loads(value))

    # from rating
    exist_rating = Rating.find(
        (Rating.userid == userid) &
        (Rating.base_url == url)
    ).all()

    if len(exist_rating):
        rating["timestamp"] = exist_rating[0].updated_timestamp
        rating["relevance"] = exist_rating[0].relevance
        rating["timeliness"] = exist_rating[0].timeliness

    # check value
    redis_ret.update(rating)
    return redis_ret


def make_message(type, pubid, event_name, message, date, show_flag, unread_flag, need_save_flag=True):
    return {
        'type' : type,
        'id': pubid,
        'title': event_name,
        'message': message,
        'date': date,
        'show_flag': show_flag,
        'unread_flag': unread_flag,
        'need_save_flag': need_save_flag,
    }

@api_config(
    versions=["v1", "v2"],
    route_name="api.message",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
    link_name="message",
    description="Get the Message",
)
def message(request):
    response = []
    day_ahead = 3
    userid = request.authenticated_userid
    request_type = request.GET.get("q")
    all = request.find_service(name="organisation_event").get_by_days(day_ahead)

    tad_url =  urljoin(request.registry.settings.get("tad_url"), "task_classification")
    tad_response = None
    try:
        tad_response = requests.get(tad_url, params={"userid": userid})
        tad_result = tad_response.json()
        response.append(
            make_message(
                "instant_message",
                datetime.now().strftime("%S%M%H%d%m%Y") + "_" +split_user(userid)["username"],
                "Expert trace recommendation",
                tad_result['message'],
                date.today().strftime("%d/%m/%Y"),
                True if tad_result['certainty'] else False, True, False)
        )
    except Exception as e:
        response.append(
            make_message(
                "error_message",
                "pubid",
                "Error",
                str(e) + "status code: " + str(tad_response.status_code) if tad_response else str(e),
                date.today().strftime("%d/%m/%Y"),
                True, True, False)
        )

    for item in all:
        show_flag = False
        unread_flag = False
        if item.date.date() >= date.today():
            ret = request.find_service(OrganisationEventPushLogService).fetch_by_userid_and_pubid(userid, item.pubid)
            if not ret:
                request.find_service(OrganisationEventPushLogService).create(userid, item.pubid)
                show_flag = True
                unread_flag = True
            elif ret and ret.dismissed:
                show_flag = True
                unread_flag = False
            else:
                show_flag = False
                unread_flag = False
        response.append(make_message(request_type, item.pubid, item.event_name, item.text, item.date.strftime("%d/%m/%Y"), show_flag, unread_flag))
    return response

@api_config(
    versions=["v1", "v2"],
    route_name="api.event",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="event",
    description="Create an user interaction",
)
def event(request):
    event = request.json_body

    # print("event api", event)

    add_user_event(
        userid=request.authenticated_userid,
        event_type=event["event_type"],
        timestamp=event["timestamp"],
        tag_name=event["tag_name"],
        text_content=event["text_content"],
        base_url=event["base_url"],
        ip_address=request.client_addr,
        interaction_context="",
        event_source="",
        x_path="",
        offset_x=0.0,
        offset_y=0.0,
        doc_id="",
        region="",
        )
    return {
        "succ": "event has been saved"
    }


@api_config(
    versions=["v1", "v2"],
    route_name="api.rating",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="rating",
    description="Rating",
)
def rating(request):
    userid = request.authenticated_userid
    data = request.json_body # dict
    data["userid"] = userid
    rating = None

    # userid
    # timestamp
    # base_url
    # releavace
    # timeliness
    if "timestamp" not in data or "relevance" not in data or "timeliness" not in data:
        return {"error": "miss args(timestamp/relevance/timeliness)"}

    try:
        exist_rating = Rating.find(
            (Rating.userid == userid) &
            (Rating.base_url == data["base_url"])
        ).all()
        if len(exist_rating) == 1:
            rating = exist_rating[0]
            rating.relevance = data["relevance"]
            rating.timeliness = data["timeliness"]
            rating.updated_timestamp = data["timestamp"]
            rating.updated = datetime.now()
        elif len(exist_rating) > 1:
            return {"error": "multiple exist_rating error"}
        else:
            data["created_timestamp"] = data["timestamp"]
            data["updated_timestamp"] = data["timestamp"]
            data["created"] = datetime.now()
            data["updated"] = datetime.now()
            rating = Rating(**data)
        rating.save()
    except Exception as e:
        return {"error" : repr(e)}
    else:
        return {
            "succ": "rating" + rating.pk + "has been saved"
        }


@api_config(
    versions=["v1", "v2"],
    route_name="api.slack",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="slack",
    description="Slack",
)
def slack(request):
    # app = request.registry["slack.app"]
    # result = app.client.conversations_list()
    # print("result", result)
    pass


@api_config(
    versions=["v1", "v2"],
    route_name="api.user_event",
    request_method="GET",
    # permission=Permission.Annotation.CREATE,
    link_name="user_event",
    description="Get User Event",
)
def user_event(request):
    kwargs = request.params.dict_of_lists()

    if 'userid' in kwargs and 'index' in kwargs:
        pagesize = request.params['pagesize'] if 'pagesize' in kwargs else 25
        sortby = request.params['sortby'] if 'sortby' in kwargs else 'decs'

        userid = request.params['userid']
        index = request.params['index']

        return {"succ": "user event", "user_id": userid, "index": index, "pagesize": pagesize, "sortby": sortby}

    else:
        return {'failed': "miss params"}