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
from datetime import datetime, date, timezone
import json
import os
import openai
import html2text
import logging
import re
import requests
import shutil
from redis_om import get_redis_connection
from urllib.parse import urljoin, urlparse, urlunparse, unquote

from h.exceptions import InvalidUserId
from h.security import Permission
from h.views.api.config import api_config
from h.models_redis import UserEvent, Rating
from h.models_redis import get_highlights_from_openai, create_user_event, add_user_event
from h.models_redis import get_user_status_by_userid, set_user_status
from h.models_redis import get_user_event, update_user_event, fetch_all_user_events_by_session
from h.models_redis import fetch_user_event_by_timestamp, batch_user_event_record, is_task_page
from h.models_redis import add_push_record, delete_push_record, fetch_push_record, stop_pushing, same_as_previous
from h.services import OrganisationEventPushLogService


log = logging.getLogger(__name__)

text_maker = html2text.HTML2Text()
text_maker.ignore_links = True
text_maker.ignore_images = True

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


def remove_url_parameters(url):
    # Parse the URL into components
    parsed_url = urlparse(url)

    # Reconstruct the URL without the query parameters
    url_without_params = urlunparse(parsed_url._replace(query=""))

    return url_without_params


def markdown2plain(content):
    plain_text = re.sub(r'(^|\s)#{1,6}\s', '', content)
    # Remove bold and italic formatting
    plain_text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', plain_text)
    plain_text = re.sub(r'(\*|_)(.*?)\1', r'\2', plain_text)

    # Remove links and images
    plain_text = re.sub(r'!\[.*?\]\(.*?\)', '', plain_text)
    plain_text = re.sub(r'\[.*?\]\(.*?\)', '', plain_text)

    # Remove lists
    plain_text = re.sub(r'^\s*[-*]\s+', '', plain_text, flags=re.MULTILINE)

    # Clean up extra spaces and newlines
    plain_text = re.sub(r'\s+', ' ', plain_text).strip()

    return plain_text


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
        # print("meta", meta)
        parsed_url = urlparse(meta["link"])
        host_name = parsed_url.netloc
        name = meta["name"]
        if name == "":
            name = host_name + parsed_url.path.split("/")[-1]
        if not name.endswith(".html"):
            name = name + ".html"
        try:
            create_user_event("server-record", "UPLOAD REQUEST", name, request.url, userid)
            filepath = os.path.join(root_dir, name)
            if os.path.exists(filepath):
                print("exist file", filepath)
                create_user_event("server-record", "UPLOAD RESPONSE FAILED", name + " already exists", request.url,
                                  userid)
                return {"error": name + " already exists"}
            with open(filepath, "wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
        except Exception as e:
            create_user_event("server-record", "UPLOAD RESPONSE FAILED", name + "error:" + repr(e), request.url, userid)
            return {"error": repr(e)}

        relavtive_path = os.path.relpath(filepath, settings.get("user_root"))
        create_user_event("server-record", "UPLOAD RESPONSE SUCC", name, request.url, userid)

        content = meta.get("content", "")
        page_url = meta.get('link')
        if page_url and page_url != '':
            plain_text = ''
            try:
                # plain_text = html2text.html2text(content)
                parser = html2text.HTML2Text()
                parser.ignore_links = True
                parser.ignore_images = True
                markdown_text = parser.handle(content)
                plain_text = markdown2plain(markdown_text)
            except Exception as e:
                print("error",e)
                log.error("html2text", e)
                plain_text = ''

            url = urljoin(request.registry.settings.get("query_url"), "upload")

            data = {
                'content': plain_text,
                'title': name,
                'url': page_url,
                'repository': 'user-uploaded'#request.authenticated_userid
            }

            try:
                create_user_event("server-record", "INGEST REQUEST", plain_text[0:30], page_url,userid)
                response = requests.post(url, data=data)
            except Exception as e:
                create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:" + repr(e), page_url, userid)
                return {"error": repr(e)}
            else:
                if response.status_code != 200:
                    create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:TA B proxy error", url, userid)
                    return {"error": "TA B proxy error"}
                return {"succ": {
                    "depth": 0,
                    "id": root_dir,
                    "link": os.path.join(settings.get("user_root_url"), "static", relavtive_path),
                    "name": name,
                    "path": filepath,
                    "type": "file"
                }}
        else:
            return {"error": "invaild link or content"}

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
            create_user_event("server-record", "UPLOAD REQUEST FROM GOOGLE FAIL", name, request.url, userid)
            return {"error": repr(e)}
        else:
            create_user_event("server-record", "UPLOAD REQUEST FROM GOOGLE SUCC", name, request.url, userid)
            succ_response = {"succ": {
                "depth": 0,
                "id": root_dir,
                "link": os.path.join(settings.get("user_root_url"), "static", relavtive_path),
                "name": name,
                "path": filepath,
                "type": "file"
            }}
            print("path", filepath)
            if not name.lower().endswith('.pdf'):  # if not pdf file
                print('not pdf')
                return succ_response
            url = urljoin(request.registry.settings.get("query_url"), "upload")
            data = {"url": os.path.join(settings.get("user_root_url"), "static", relavtive_path)}
            return ingest(url, name, filepath, data, userid, succ_response)

    parent_path = meta["id"]
    file_path = meta["path"]
    depth = int(meta["depth"])
    name = meta["name"]
    if file_path == "" or name == "":
        create_user_event("server-record", "UPLOAD FAILED", name, request.url, userid)
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
        create_user_event("server-record", "UPLOAD REQUEST", name, request.url, userid)
        # check the user directory
        if not os.path.exists(parent_path):
            os.mkdir(parent_path)

        if os.path.exists(file_path):
            create_user_event("server-record", "UPLOAD RESPONSE FAILED", name + " already exists", request.url, userid)
            return {"error": name + " already exists"}

        with open(file_path, "wb") as output_file:
            shutil.copyfileobj(input_file, output_file)
        with open(file_path, "rb") as source_file:
            with open(public_file_path, "wb") as output_file:
                shutil.copyfileobj(source_file, output_file)
    except Exception as e:
        create_user_event("server-record", "UPLOAD RESPONSE FAILED", name + "error:" + repr(e), request.url, userid)
        return {"error": repr(e)}

    create_user_event("server-record", "UPLOAD RESPONSE SUCC", name, request.url, userid)
    succ_response = {"succ": {
        "depth": depth,
        "id": parent_path,
        "link": os.path.join(settings.get("user_root_url"), "static", relavtive_path),
        "name": name,
        "path": file_path,
        "type": "file"
    }}

    # transfer to TA B
    url = urljoin(request.registry.settings.get("query_url"), "upload")
    data = {"url": os.path.join(settings.get("user_root_url"), "static", relavtive_path)}
    if not name.lower().endswith('.pdf'):  # if not pdf file
        print('upload not pdf')
        return succ_response
    return ingest(url, name, file_path, data, userid, succ_response)


def ingest(url, name, file_path, data, userid, succ_response):
    local_file = open(file_path, "rb")
    files = {"myFile": (name, local_file)}
    try:
        # start ingest
        print('start ingesting')
        create_user_event("server-record", "INGEST REQUEST", name, url, userid)
        response = requests.post(url, files=files, data=data)
        # result = response.json()
    except Exception as e:
        create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:" + repr(e), url, userid)
        return {"error": repr(e)}
    else:
        if response.status_code != 200:
            create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:TA B proxy error", url, userid)
            return {"error": "TA B proxy error"}
    try:
        result = response.json()
    except Exception as e:
        create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:" + repr(e), url, userid)
        return {"error": repr(e)}
    else:
        # check the ingesting is succ?
        # if "error" in result:
        #     if "[the ingestion failed]" in result["error"]:
        #         succ_response["tab"] = result["error"]
        #     else:
        #         return result
        if result["status"] == 404:
            create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:" + result["message"], url,
                              userid)
            return {"error": result["message"]}
        elif result["status"] == 303:
            create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:303 " + result["message"], url,
                              userid)
            return {"error": "The file was ingested successfully [CODE: 303]"}
            pass
        elif result["status"] == 304:
            create_user_event("server-record", "INGEST RESPONSE FAILED", name + " error:304 " + result["message"], url,
                              userid)
            return {"error": result["message"]}
        elif result["status"] == 200:
            create_user_event("server-record", "INGEST RESPONSE SUCC", name, url, userid)
            return succ_response

    local_file.close()
    # return succ_response


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
        create_user_event("server-record", "DELETE REQUEST", filename, request.url, userid)
        print("file_path", file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        print("public_file_path", public_file_path)
        if os.path.exists(public_file_path):
            os.remove(public_file_path)
        create_user_event("server-record", "DELETE RESPONSE SUCC", filename, request.url, userid)
    except Exception as e:
        create_user_event("server-record", "DELETE RESPONSE FAIL", filename, request.url, userid)
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
        'type': 'dir',  # dir | file
        'link': current_path,
        'children': [],
        'depth': depth,
    }
    with os.scandir(dir) as it:
        for entry in it:
            if entry.is_file():
                creation_time = 0
                try:
                    stat_info = entry.stat()
                    creation_time = stat_info.st_ctime
                except OSError as e:
                    print(f"Error accessing file {entry.name}: {e}")
                file_node = {
                    'path': os.path.join(dir, entry.name),
                    'id': dir,
                    'name': entry.name,
                    'type': 'file',
                    'link': os.path.join(current_path, entry.name),
                    'creation_time': creation_time,
                    'children': [],
                    'depth': depth,
                }
                directory_node['children'].append(file_node)
                directory_node['children'].sort(key=lambda x: x.get('creation_time', 0), reverse=True)
            elif entry.is_dir():
                directory_node['children'].append(
                    iterate_directory(os.path.join(dir, entry.name), entry.name, current_path, depth + 1))

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


# TODO remove
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
    data = request.json_body  # dict

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
    route_name="api.share_flow",
    request_method="DELETE",
    permission=Permission.Annotation.CREATE,
    link_name="share_flow.delete",
    description="Remove the session of the share flow",
)
def remove_expert_replay(request):
    session_id = request.GET.get("session_id")
    task_name = request.GET.get("task_name")
    user_id = request.authenticated_userid
    result = fetch_all_user_events_by_session(user_id, session_id)
    count = 0
    for item in result['table_result']:
        pk = update_user_event(item['pk'], dict(session_id='', task_name=''))
        count += 1
    return {'reset': count}


@api_config(
    versions=["v1", "v2"],
    route_name="api.share_flow",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
    link_name="share_flow.read",
    description="Get the session of the share flow",
)
def read_share_flow(request):
    return expert_replay(request)


@api_config(
    versions=["v1", "v2"],
    route_name="api.expert_replay",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
    link_name="expert_replay",
    description="get the session of the expert replay",
)
def expert_replay(request):
    userID="acct:admin@localhost"
    resultAllEvents = batch_user_event_record(userID)
    return batch_steps(resultAllEvents)


#   type: string;
#   id: string;
#   url?: string;
#   description?: string;
#   title?: string;
#   position?: string;
#   image?: string | null;
#   width? : number;
#   height? : number;
#   offsetX? : number;
#   offsetY? : number;
def batch_steps(index_list):
    auxDict = []
    for resultSesions in index_list:  # For the taskName and session
        eventlist = []
        fetch_result = fetch_user_event_by_timestamp(
            resultSesions.userid,
            resultSesions.session_id,
            resultSesions.startstamp - 10 + resultSesions.start * 1000,
            resultSesions.endstamp)
        textKeydown=""
        last_click = None
        last_keyup = None
        last_change = None
        last_navigate = None
        last_scroll = None
        flagScroll=True
        lenResult=len(fetch_result)
        for i in range(lenResult):
            resultTask=fetch_result[i].dict()
            event_type = resultTask['event_type']
            if event_type!="beforeunload" and \
                event_type!="OPEN" and \
                event_type!="open" and \
                event_type!="visibilitychange" and \
                event_type!="server-record" and \
                event_type!="START" and \
                event_type!="close" and \
                str(resultTask['event_source'])!="MESSAGE" and \
                str(resultTask['event_source'])!="SIDERBAR" and \
                str(resultTask['event_source'])!="RECORDING":
                if str(resultTask['event_type'])=="scroll":
                    if last_scroll and flagScroll:
                        eventDescription=getTextbyEvent("scroll",str(resultTask['text_content']).split(":")[0],"")
                        if last_scroll["description"] != eventDescription:
                            last_scroll = {"type": str(resultTask['event_type']), "url" : str(resultTask['base_url']), "xpath" : str(resultTask['x_path']),"text" : str(resultTask['text_content']), "offsetX": resultTask['offset_x'], "offsetY": resultTask['offset_y'], "position": "N/A", "width":resultTask['width'], "height":resultTask['height'], "title": resultTask.get('title', resultTask['event_source']), "description" : str(eventDescription), "image": resultTask['image']}
                            eventlist.append(last_scroll)
                            flagScroll = False
                    elif not last_scroll:
                        eventDescription=getTextbyEvent("scroll",str(resultTask['text_content']).split(":")[0],"")
                        last_scroll = {"type": str(resultTask['event_type']), "url" : str(resultTask['base_url']), "xpath" : str(resultTask['x_path']),"text" : str(resultTask['text_content']), "offsetX": resultTask['offset_x'], "offsetY": resultTask['offset_y'], "position": "N/A", "width":resultTask['width'], "height":resultTask['height'], "title": resultTask.get('title', resultTask['event_source']), "description" : str(eventDescription), "image": resultTask['image']}
                        eventlist.append(last_scroll)
                        flagScroll = False
                elif resultTask['event_type'] == 'navigate':
                    # if last_keyup:
                    #     print('print navigate>>>', resultTask['interaction_context'])
                    #     eventlist.append(createKeyupEvent(**last_keyup))
                    #     last_keyup = None
                    if not resultTask['title']:
                        parese_url = urlparse(resultTask['base_url'])
                        resultTask['title'] = parese_url.netloc
                    if not last_navigate:
                        last_navigate = {
                        "type": resultTask['event_type'],
                        "url": resultTask['base_url'],
                        "xpath": '',
                        "text": '',
                        "offsetX": 0,
                        "offsetY": 0,
                        "position": "N/A",
                        "title":resultTask['title'],
                        "description" : 'Go to ',
                        }
                        eventlist.append(last_navigate)

                    if last_navigate.get("title") != resultTask['title'] and remove_url_parameters(last_navigate['url']) != remove_url_parameters(resultTask['base_url']):
                        last_navigate = {
                            "type": resultTask['event_type'],
                            "url" : resultTask['base_url'],
                            "xpath" : '',
                            "text" : '',
                            "offsetX": 0,
                            "offsetY": 0,
                            "position": "N/A",
                            "title":resultTask['title'],
                            "description" : 'Go to ',
                            }
                        eventlist.append(last_navigate)
                    flagScroll=False
                elif str(resultTask['event_type'])=="recording":
                    # if last_keyup:
                    #     print('print recording>>>')
                    #     # eventlist.append(last_keyup)
                    #     eventlist.append(createKeyupEvent(**last_keyup))
                    #     last_keyup = None
                    eventlist.append({"type": resultTask['event_type'], "url" : resultTask['base_url'], "xpath" : '',"text" : '', "offsetX": 0, "offsetY": 0, "position": "N/A", "title":resultTask['title'], "description" : resultTask['tag_name'] + ' to ', "image": resultTask['image']})
                elif event_type == "getfocus":
                    if last_change:
                        eventlist.append(last_change)
                        last_change = None
                    title = resultTask['title']
                    if not resultTask['title']:
                        title = urlparse(resultTask['base_url']).netloc
                    eventlist.append({
                        "type": resultTask['event_type'],
                        "url" : resultTask['base_url'],
                        "xpath" : '',
                        "text" : '',
                        "offsetX": 0,
                        "offsetY": 0,
                        "position": "N/A",
                        "title": title,
                        "description" : resultTask['tag_name'] + ' to the ' + title,
                        "image": resultTask['image']
                    })
                elif event_type=="keyup":
                    interaction_context = resultTask.get('interaction_context', '')
                    xpath = resultTask.get('x_path', None)
                    key = None
                    name = None
                    value = None
                    print("\nkeyup event interaction_context", interaction_context, 'xpath', xpath)
                    try:
                        interaction_context = json.loads(interaction_context)
                    except json.JSONDecodeError:
                        break
                    else:
                        key = interaction_context.get('key', None)
                        name = interaction_context.get('name', None)
                        value = interaction_context.get('value', None)

                    # if last_keyup and last_keyup['xpath'] != xpath:
                    #     # last_keyup.pop('interaction_context')
                    #     # eventlist.append(last_keyup)
                    #     eventlist.append(createKeyupEvent(**last_keyup))
                    #     last_keyup = None

                    if not value:
                        if last_keyup and key:
                            print(">>>", last_keyup)
                            # last_keyup_value = last_keyup['interaction_context']['value']
                            last_keyup_value = last_keyup['value']
                            if key.lower() == 'shift' or \
                                key.lower() == 'control' or \
                                key.lower() == 'meta' or \
                                key.lower() == 'enter' or \
                                key.lower() == 'capslock' or \
                                key.lower() == 'arrowright' or \
                                key.lower() == 'arrowleft'or \
                                key.lower() == 'arrowup'or \
                                key.lower() == 'arrowdown':
                                pass
                            elif key.lower() == 'backspace':
                                last_keyup_value = last_keyup_value[:-1]
                            else:
                                last_keyup_value += key

                            # last_keyup = {
                            #     'type': resultTask['event_type'],
                            #     'url': resultTask['base_url'],
                            #     "xpath" : resultTask.get('x_path'),
                            #     "title": resultTask.get('title', resultTask['event_source']),
                            #     "description" : "Typing \"" + last_keyup_value + '"' + ((" in the \"" + name + "\" input box") if name else ""),
                            #     "interaction_context": {'key': key, 'value': last_keyup_value, 'name': name},
                            #     }
                            last_keyup = {
                                'event_type': resultTask['event_type'],
                                'url': resultTask['base_url'],
                                "xpath" : resultTask.get('x_path'),
                                "title": resultTask.get('title', resultTask['event_source']),
                                'key': key,
                                'name': name,
                                'value': last_keyup_value
                            }
                        elif (not last_keyup) and key:
                            if key.lower() == 'shift' or \
                                key.lower() == 'control' or \
                                key.lower() == 'meta' or \
                                key.lower() == 'enter' or \
                                key.lower() == 'capslock' or \
                                key.lower() == 'arrowright' or \
                                key.lower() == 'arrowleft'or \
                                key.lower() == 'arrowup'or \
                                key.lower() == 'arrowdown':
                                key=''
                            elif key.lower() == 'backspace':
                                key=''
                            else:
                                pass
                            # last_keyup = {
                            #     'type': resultTask['event_type'],
                            #     'url': resultTask['base_url'],
                            #     "xpath" : resultTask.get('x_path'),
                            #     "title": resultTask.get('title', resultTask['event_source']),
                            #     "description" : "Typing \"" + key + '"' + ((" in the \"" + name + "\" input box") if name else ""),
                            #     "interaction_context": {'key': key, 'value': key, 'name': name},
                            #     }
                            last_keyup = {
                                'event_type': resultTask['event_type'],
                                'url': resultTask['base_url'],
                                "xpath" : resultTask.get('x_path'),
                                "title": resultTask.get('title', resultTask['event_source']),
                                'key': key,
                                'name': name,
                                'value': key
                            }
                    else:
                        # last_keyup = {
                        #     'type': resultTask['event_type'],
                        #     'url': resultTask['base_url'],
                        #     "xpath" : resultTask.get('x_path'),
                        #     "title": resultTask.get('title', resultTask['event_source']),
                        #     "description" : "Typing \"" + value + '"'+ ((" in the \"" + name + "\" input box") if name else ""),
                        #     "interaction_context": {'key': key, 'value': value, 'name': name},
                        #     }
                        last_keyup = {
                            'event_type': resultTask['event_type'],
                            'url': resultTask['base_url'],
                            "xpath" : resultTask.get('x_path'),
                            "title": resultTask.get('title', resultTask['event_source']),
                            'key': key,
                            'name': name,
                            'value': value
                        }
                elif event_type == 'change':
                    print("change event",
                          'tag', resultTask['tag_name'],
                          'text_content', resultTask['text_content'],
                          'interaction_context', resultTask['interaction_context'],
                          'event_source', resultTask['event_source'],
                          'x_path', resultTask['x_path'],'\n')
                    tag = resultTask['tag_name']
                    interaction_context = resultTask['text_content']
                    xpath = resultTask['x_path']
                    if tag.lower() == 'input':
                        # 'checkbox'
                        interaction_context = resultTask['interaction_context']
                        input_type = None
                        try:
                            interaction_context = json.loads(interaction_context)
                        except json.JSONDecodeError:
                            pass
                        else:
                            input_type = interaction_context.get('type', None)

                        if input_type == 'checkbox': # Edit Mode
                            width = resultTask['width']
                            height = resultTask['height']
                            offset_x = resultTask['offset_x']
                            offset_y = resultTask['offset_y']
                            title = resultTask['title']
                            image = resultTask['image']
                            if last_click and last_click['xpath'] == resultTask['x_path']:
                                width = last_click['width']
                                height = last_click['height']
                                offset_x = last_click['offset_x']
                                offset_y = last_click['offset_y']
                                title = last_click['text']
                                image = last_click['image']
                            eventPosition=getPositionViewport(width,height,offset_x,offset_y)
                            text_content = resultTask.get('text_content','').replace('\n', ' ').replace('\t', ' ').replace('\r', ' ').strip()
                            eventDescription=getTextbyEvent(event_type,text_content,eventPosition)

                            interaction_context = resultTask['interaction_context']
                            description = 'Check the checkbox'
                            try:
                                interaction_context = json.loads(interaction_context)
                            except json.JSONDecodeError:
                                pass
                            else:
                                name = interaction_context.get('name', None)
                                value = interaction_context.get('value', None)
                                if name and value:
                                    if value.isdigit():
                                        value = 'off' if int(value) == 0 else 'on'
                                        description = "Turn " + value + " the \"" + name +"\""
                                    if value.lower() == 'off' or value.lower() == 'on':
                                        description = "Turn " + value + " the \"" + name +"\""
                                    if value.lower() == 'false':
                                        description = "Uncheck the \"" + name + "\" checkbox"
                                    if value.lower() == 'true':
                                        description = "Check the \"" + name + "\" checkbox"

                                eventlist.append({
                                    "type": 'click',
                                    "url" : resultTask['base_url'],
                                    "xpath" : resultTask['x_path'],
                                    "text" : text_content,
                                    "offsetX": offset_x,
                                    "offsetY": offset_y,
                                    "position": eventPosition,
                                    "title": title,
                                    "width": width,
                                    "height": height,
                                    "description" : description,
                                    "image": image})
                        else:
                            interaction_context = resultTask['interaction_context']
                            description = 'Type '
                            try:
                                interaction_context = json.loads(interaction_context)
                            except json.JSONDecodeError:
                                pass
                            else:
                                name = interaction_context.get('name', None)
                                value = interaction_context.get('value', None)
                                if name and value:
                                    description = "Type \"" + value

                            eventlist.append({
                                "type": "keyup",
                                "url" : resultTask.get('base_url', ''),
                                "xpath" : resultTask['x_path'],
                                "text" : resultTask.get('text_content',''),
                                "position": str(eventPosition),
                                "title": resultTask['title'],
                                "width": width,
                                "height": height,
                                "description" : description,
                                "image": resultTask['image'] if 'image' in resultTask else None
                            })
                    elif tag.lower() == 'textarea': # last keyup
                        value = resultTask.get('text_content', '')
                        interaction_context = resultTask.get('interaction_context', '')
                        description = 'Type '
                        try:
                            interaction_context = json.loads(interaction_context)
                        except json.JSONDecodeError:
                            pass
                        else:
                            value = interaction_context.get('value')
                            if value:
                                description = "Type \"" + value
                                # eventlist.append({
                                #     "type": "keyup",
                                #     "url" : resultTask.get('url', ''),
                                #     "xpath" : resultTask['x_path'],
                                #     "text" : resultTask.get('text_content',''),
                                #     "position": str(eventPosition),
                                #     "title": resultTask['title'],
                                #     "width": width,
                                #     "height": height,
                                #     "description" : description,
                                #     "image": resultTask['image'] if 'image' in resultTask else None
                                # })
                                last_change = {
                                    "type": "keyup",
                                    "url" : resultTask.get('url', ''),
                                    "xpath" : resultTask['x_path'],
                                    "text" : resultTask.get('text_content',''),
                                    "position": str(eventPosition),
                                    "title": resultTask['title'],
                                    "width": width,
                                    "height": height,
                                    "description" : description,
                                    "image": resultTask['image'] if 'image' in resultTask else None
                                }
                    elif tag.lower() == 'select': # last click
                        print("lask click select>>>")
                        if last_click['xpath'] == xpath:
                            width = last_click['width']
                            height = last_click['height']
                            offset_x = last_click['offset_x']
                            offset_y = last_click['offset_y']
                            eventPosition=getPositionViewport(width,height,offset_x,offset_y)
                            text_content = resultTask.get('text_content','').replace('\n', ' ').replace('\t', ' ').replace('\r', ' ').strip()
                            eventDescription=getTextbyEvent(event_type,text_content,eventPosition)
                            print("event description", eventDescription)

                            interaction_context = resultTask['interaction_context']
                            description = 'Select the option'
                            try:
                                interaction_context = json.loads(interaction_context)
                            except json.JSONDecodeError:
                                pass
                            else:
                                name = interaction_context.get('name', None)
                                value = interaction_context.get('value', None)
                                if name and value:
                                    if value.isdigit():
                                        value = 'False' if int(value) == 0 else 'True'
                                    description = "Select the option \"" + value + "\" in the \"" + name +"\" dropdown"

                            eventlist.append({
                                "type": "select",
                                "url" : last_click['url'],
                                "xpath" : last_click['xpath'],
                                "text" : last_click['text'],
                                "offsetX": offset_x,
                                "offsetY": offset_y,
                                "position": str(eventPosition),
                                "title": last_click['title'],
                                "width": width,
                                "height": height,
                                "description" : description,
                                "image": resultTask['image'] if 'image' in resultTask else None
                            })
                elif str(resultTask['event_type'])=="keydown":# keyboard Events
                    textKeydown=getKeyboard(textKeydown,str(resultTask['text_content']))
                    if i<lenResult:
                        if i+1 < len(fetch_result) and str(fetch_result[i+1]['event_type'])!="keydown": #Is last keydownEvent
                            eventDescription=getTextbyEvent("keydown",textKeydown,"")
                            textKeydown=""
                            eventlist.append({"type": str(resultTask['event_type']), "url" : str(resultTask['base_url']), "xpath" : str(resultTask['x_path']),"text" : str(resultTask['text_content']), "offsetX": resultTask['offset_x'], "offsetY": resultTask['offset_y'], "position": "N/A", "title": resultTask.get('title', resultTask['event_source']), "description" : str(eventDescription), "image": resultTask['image']})
                    flagScroll=True
                elif event_type == 'click' or event_type == 'pointerdown': #CLICK
                    print("click event", event_type,
                          'tag_name', resultTask['tag_name'],
                          'text_content', resultTask['text_content'],
                          'interaction_context', resultTask['interaction_context'],
                          'event_source', resultTask['event_source'],
                          'x_path',resultTask['x_path'])
                    if last_change:
                        eventlist.append(last_change)
                        last_change = None
                    tag = resultTask['tag_name']
                    if tag == "SIDEBAR-TAB" or tag == "HYPOTHESIS-SIDEBAR":
                        pass
                    else:
                        width = resultTask['width']
                        height = resultTask['height']
                        offset_x = resultTask['offset_x']
                        offset_y = resultTask['offset_y']
                        eventPosition=getPositionViewport(width,height,offset_x,offset_y)
                        text_content = resultTask.get('text_content','').replace('\n', ' ').replace('\t', ' ').replace('\r', ' ').strip()
                        eventDescription=getTextbyEvent(event_type,text_content,eventPosition)
                        if tag == 'SELECT':
                            description = "Click to select"
                            eventlist.append({
                                "type": resultTask['event_type'],
                                "url" : resultTask['base_url'],
                                "xpath" : resultTask['x_path'],
                                "text" : '',
                                "offsetX": offset_x,
                                "offsetY": offset_y,
                                "position": eventPosition,
                                "title": resultTask['title'],
                                "width": width,
                                "height": height,
                                "description" : description,
                                "image": resultTask['image']
                                })
                        elif tag == 'INPUT':
                            interaction_context = resultTask['interaction_context']
                            input_type = None
                            try:
                                interaction_context = json.loads(interaction_context)
                            except json.JSONDecodeError:
                                pass
                            else:
                                input_type = interaction_context.get('type', None)
                                name = interaction_context.get('name', None)
                                value = interaction_context.get('value', None)

                            if input_type == 'checkbox':
                                pass
                            elif input_type == 'submit':
                                pass
                            elif input_type == 'text':
                                width = resultTask['width']
                                height = resultTask['height']
                                offset_x = resultTask['offset_x']
                                offset_y = resultTask['offset_y']
                                eventPosition=getPositionViewport(width,height,offset_x,offset_y)
                                interaction_context = resultTask['interaction_context']
                                description = "Click " + eventPosition
                                try:
                                    interaction_context = json.loads(interaction_context)
                                except json.JSONDecodeError:
                                    pass
                                else:
                                    name = interaction_context.get('name')
                                    if name:
                                        description = 'Click on "' + name + '" at ' + eventPosition

                                eventlist.append({
                                    "type": resultTask['event_type'],
                                    "url" : resultTask['base_url'],
                                    "xpath" : resultTask['x_path'],
                                    "text" : '',
                                    "offsetX": offset_x,
                                    "offsetY": offset_y,
                                    "position": eventPosition,
                                    "title": resultTask['title'],
                                    "width": width,
                                    "height": height,
                                    "description" : description,
                                    "image": resultTask['image']})
                            else:
                                eventlist.append({
                                    "type": event_type,
                                    "url" : str(resultTask['base_url']),
                                    "xpath" : str(resultTask['x_path']),
                                    "text" : text_content,
                                    "offsetX": resultTask['offset_x'],
                                    "offsetY": resultTask['offset_y'],
                                    "position": eventPosition,
                                    "title": resultTask.get('title', resultTask['event_source']),
                                    "width":resultTask['width'],
                                    "height":resultTask['height'],
                                    "description" : str(eventDescription),
                                    "image": resultTask['image'] if 'image' in resultTask else None})
                        elif tag == 'SPAN':
                            text_content = resultTask.get('text_content','').replace('\n', ' ').replace('\t', ' ').replace('\r', ' ').strip()
                            eventlist.append({
                                "type": event_type,
                                "url" : str(resultTask['base_url']),
                                "xpath" : str(resultTask['x_path']),
                                "text" : text_content,
                                "offsetX": resultTask['offset_x'],
                                "offsetY": resultTask['offset_y'],
                                "position": eventPosition,
                                "title": resultTask.get('title', resultTask['event_source']),
                                "width":resultTask['width'],
                                "height":resultTask['height'],
                                "description" : getTextbyEvent(event_type, text_content, eventPosition),
                                "image": resultTask['image'] if 'image' in resultTask else None})
                        else:
                            print("here 3", tag)
                            eventlist.append({
                                "type": event_type,
                                "url" : str(resultTask['base_url']),
                                "xpath" : str(resultTask['x_path']),
                                "text" : text_content,
                                "offsetX": resultTask['offset_x'],
                                "offsetY": resultTask['offset_y'],
                                "position": str(eventPosition),
                                "title": resultTask.get('title', resultTask['event_source']),
                                "width":resultTask['width'],
                                "height":resultTask['height'],
                                "description" : str(eventDescription),
                                "image": resultTask['image'] if 'image' in resultTask else None})
                    last_click =  {
                            'type': event_type,
                            'url': resultTask['base_url'],
                            "xpath" : resultTask.get('x_path'),
                            'text': resultTask.get('text_content'),
                            'interaction_context': resultTask.get('interaction_context'),
                            'event_source': resultTask.get('event_source'),
                            'width': resultTask['width'],
                            'height': resultTask['height'],
                            'offset_x': resultTask['offset_x'],
                            'offset_y': resultTask['offset_y'],
                            "title": resultTask.get('title', resultTask['event_source']),
                            "image" : resultTask.get('image'),
                            }
                    flagScroll=True
                elif event_type == 'submit':
                    xpath = resultTask['x_path']
                    print("submit event", event_type,
                          'tag_name', resultTask['tag_name'],
                          'text_content', resultTask['text_content'],
                          'interaction_context', resultTask['interaction_context'],
                          'event_source', resultTask['event_source'],
                          'x_path',resultTask['x_path'])
                    if last_change:
                        eventlist.append(last_change)
                        last_change = None
                    value = resultTask.get('text_content')
                    description = 'Click the \"' + value + '\" to submit'
                    eventlist.append({
                        "type": event_type,
                        "url" : resultTask['base_url'],
                        "xpath" : resultTask['x_path'],
                        "text" : text_content,
                        "offsetX": last_click['offset_x'] if (last_click and last_click['xpath'] == xpath) else resultTask['offset_x'],
                        "offsetY": last_click['offset_y'] if (last_click and last_click['xpath'] == xpath) else resultTask['offset_y'],
                        "position": str(eventPosition),
                        "title": resultTask.get('title', resultTask['event_source']),
                        "width":resultTask['width'],
                        "height":resultTask['height'],
                        "description" : description,
                        "image": resultTask['image'] if 'image' in resultTask else None})
                else:
                    if str(resultTask['text_content']) != "" and str(resultTask['tag_name']) != "SIDEBAR-TAB" and str(resultTask['tag_name']) != "HYPOTHESIS-SIDEBAR":
                        if last_change:
                            eventlist.append(last_change)
                            last_change = None
                        width = resultTask['width']
                        height = resultTask['height']
                        offset_x = resultTask['offset_x']
                        offset_y = resultTask['offset_y']
                        event_type = resultTask['event_type']
                        if event_type == 'pointerdown':
                            event_type = 'click'
                        if event_type == 'pointerdown' or event_type == 'click':
                            print("22223click event", event_type,
                                  'tag_name', resultTask['tag_name'],
                                  'text_content', resultTask['text_content'],
                                  'interaction_context', resultTask['interaction_context'],
                                  'event_source', resultTask['event_source'],
                                  'x_path',resultTask['x_path'])
                        eventPosition=getPositionViewport(width,height,offset_x,offset_y)
                        text_content = resultTask.get('text_content','').replace('\n', ' ').replace('\t', ' ').replace('\r', ' ').strip()
                        eventDescription=getTextbyEvent(event_type,text_content,eventPosition)
                        if eventDescription!="No description":
                            eventlist.append({"type": event_type, "url" : str(resultTask['base_url']), "xpath" : str(resultTask['x_path']),"text" : text_content, "offsetX": resultTask['offset_x'], "offsetY": resultTask['offset_y'], "position": str(eventPosition), "title": resultTask.get('title', resultTask['event_source']), "width":resultTask['width'], "height":resultTask['height'], "description" : str(eventDescription), "image": resultTask['image'] if 'image' in resultTask else None})
                    flagScroll=True
        if lenResult< len(fetch_result) and textKeydown!="":
            eventDescription=getTextbyEvent("keydown",textKeydown,"")
            eventlist.append({"type": str(fetch_result[lenResult]['event_type']), "url" : str(fetch_result[lenResult]['base_url']), "xpath" : str(fetch_result[lenResult]['x_path']),"text" : str(fetch_result[lenResult]['text_content']), "offsetX": fetch_result[lenResult]['offset_x'], "offsetY": fetch_result[lenResult]['offset_y'], "position": "N/A", "width":resultTask['width'], "height":resultTask['height'], "title":fetch_result[lenResult].get('title', fetch_result[lenResult]['event_source']), "description" : str(eventDescription), "image": resultTask['image']})
        if resultSesions.task_name is None: task_name="test API"
        else: task_name= str(resultSesions.task_name)
        auxDict.append({
            "taskName": task_name,
            'sessionId': resultSesions.session_id,
            "timestamp": resultSesions.startstamp,
            "steps": eventlist,
            "task_name": task_name,
            "session_id": resultSesions.session_id,
            "userid": resultSesions.userid,
            "groupid": resultSesions.groupid,
            "shared": resultSesions.shared,
        })  # add the timestap for each taks
    # dictResult['data']=auxDict
    return auxDict


def createKeyupEvent(event_type, url, xpath, title, key, name, value):
    if name:
        description = "Type \"" + value + '"' + " in the \"" + name + "\" input box"
    else:
        description = "Type \"" + value + '"'

    return {
        'type': event_type,
        'url': url,
        'xpath': xpath,
        'text': '',
        "position": '',
        'title': title,
        'description': description,
        "interaction_context": {'key': key, 'value': value, 'name': name},
    }

def getKeyboard(textKeydown, character):
    if character == "Backspace":
        return (textKeydown[:-1])
    elif character == "Shift" or character == "Enter":
        return (textKeydown)
    else:
        return (textKeydown + character)


def getTextbyEvent(event_type, text_content, eventPosition):
    if len(text_content) > 100:
        text_content = text_content[0:100] + "..."
        # print("Text CONTENT: "+ text_content)
    if event_type == "click":
        if not text_content or text_content == '':
            return 'Click at ' + eventPosition
        return 'Click on "' + text_content.replace("  ", " ").replace("\n", " ") + '" at ' + eventPosition
    elif event_type == "scroll":
        return text_content.lower().capitalize() + " on the web page"
    elif event_type == "select":
        return 'Select  "' + text_content + '" at ' + eventPosition
    elif event_type == "keydown":
        return 'Type "' + text_content + '"'
    else:
        return "No description"


def getPositionViewport(screen_width, screen_height, offset_x, offset_y):
    try:
        if screen_width and screen_height and offset_x and offset_y:
            screen_width = int(screen_width)
            screen_height = int(screen_height)
            offset_x = int(offset_x)
            offset_y = int(offset_y)
            horizontal_threshold = screen_width / 4
            upper_vertical_threshold = screen_height / 4
            lower_vertical_threshold = screen_height - screen_height / 4

            if offset_y < upper_vertical_threshold:
                vertical_position = 'top'
            elif offset_y > lower_vertical_threshold:
                vertical_position = 'bottom'
            else:
                vertical_position = 'center'
                # vertical_position = 'bottom'

            if offset_x < horizontal_threshold:
                horizontal_position = 'left'
            elif offset_x > screen_width - horizontal_threshold:
                horizontal_position = 'right'
            else:
                horizontal_position = 'center'
                # horizontal_position = 'right'

            # Determine final position
            if vertical_position == 'center' and horizontal_position == 'center':
                return 'center'
            elif vertical_position == 'center' and horizontal_position != 'center':
                return f"{horizontal_position}"
            elif vertical_position != 'center' and horizontal_position == 'center':
                return f"{vertical_position}"
            elif vertical_position != 'center' and horizontal_position != 'center':
                return f"{vertical_position} {horizontal_position}"
        else:
            return 'N/A'
    except Exception as e:
        return 'N/A'


# Ivan

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


def make_message(type, pubid, event_name, message, date, show_flag, unread_flag, need_save_flag=True, extra=None):
    return {
        'type': type,
        'id': pubid,
        'title': event_name,
        'message': message,
        'date': date,
        'show_flag': show_flag,
        'unread_flag': unread_flag,
        'need_save_flag': need_save_flag,
        'extra': extra,
    }


@api_config(
    versions=["v1", "v2"],
    route_name="api.pull",
    request_method="GET",
    # permission=Permission.Annotation.CREATE,
    link_name="message",
    description="Get the Message",
)
def message(request):
    response = []
    day_ahead = 3
    defalut_interval = "30000"
    userid = request.authenticated_userid
    if not userid:
        return []

    request_type = request.GET.get("q")
    interval = request.GET.get("interval") if request.GET.get("interval") else defalut_interval
    url = request.GET.get("url")
    all = request.find_service(name="organisation_event").get_by_days(day_ahead)

    tad_url = urljoin(request.registry.settings.get("tad_url"), "task_classification")
    tad_response = None
    # only request for TAD Shareflow push when users are on task pages and the current task page has received less than 3 Shareflow Pushes
    try:
        # create_user_event("server-record", "TAD REQUEST", url, url, userid)
        tad_response = requests.get(tad_url, params={"userid": userid, "interval": int(interval), "url": unquote(url)})
        # create_user_event("server-record", "TAD RESPONSE", "succ", url, userid)
        tad_result = tad_response.json()
        print('tad_result', tad_result)
        rep_interval = tad_result["interval"] if "interval" in tad_result else defalut_interval
        message = make_message(
            "instant_message",
            datetime.now().strftime("%S%M%H%d%m%Y") + "_" + split_user(userid)["username"],
            "Need help with this task?",
            tad_result["message"],
            datetime.now().strftime("%s%f"),
            tad_result['show_flag'],
            True,
            tad_result['show_flag'],
            tad_result["task_details"]
            )
        message["interval"] = rep_interval
        message["should_next"] = True if rep_interval != -1 else False
        response.append(message)
    except Exception as e:
        # create_user_event("server-record", "TAD RESPONSE", "fail", url, userid)
        response.append(
            make_message(
                "error_message",
                "pubid",
                "Error",
                str(e) + "! status code: " + str(tad_response.status_code) if tad_response else str(e),
                datetime.now().strftime("%s%f"),
                False, True, False)
        )

    for item in all:
        show_flag = False
        unread_flag = False
        if item.date.date() >= date.today():
            ret = request.find_service(OrganisationEventPushLogService).fetch_by_userid_and_pubid(userid, item.pubid)
            if len(ret):
                ret = ret[0]
            else:
                ret = None
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
        response.append(make_message(request_type, item.pubid, item.event_name, item.text,
                                     item.date.replace(tzinfo=timezone.utc).astimezone().strftime("%s%f"), show_flag,
                                     unread_flag))
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

    #print("event api", event, request.authenticated_userid)
    if event["tag_name"] == "RECORD":
        if event["event_type"] == "START":
            set_user_status(request.authenticated_userid, event["task_name"], event["session_id"], "")
        if event["event_type"] == "END":
            set_user_status(request.authenticated_userid, "", "", "")

    session_id = get_user_status_by_userid(request.authenticated_userid).session_id if event["session_id"] == "" else \
    event["session_id"]
    task_name = get_user_status_by_userid(request.authenticated_userid).task_name if event["task_name"] == "" else \
    event["task_name"]
    add_user_event(
        userid=request.authenticated_userid,
        event_type=event["event_type"],
        timestamp=event["timestamp"],
        tag_name=event["tag_name"],
        text_content=event["text_content"],
        base_url=event["base_url"],
        ip_address=request.client_addr,
        interaction_context=event["interaction_context"],
        event_source=event["event_source"],
        x_path=event["x_path"],
        offset_x=event["offset_x"],
        offset_y=event["offset_y"],
        doc_id=event["doc_id"],
        region="",
        session_id=session_id,
        task_name=task_name,
        width=event["width"],
        height=event["height"],
        image=event['image'] if 'image' in event else None,
        title=event['title'] if 'title' in event else None,
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
    data = request.json_body  # dict
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
        return {"error": repr(e)}
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
