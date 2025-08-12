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
from pyramid import i18n
from pyramid.httpexceptions import HTTPBadRequest

from h.events import ShareflowMetadataEvent
from h.security import Permission
from h.traversal import UserEventRecordContext
from h.views.api.config import api_config
from h.views.api.exceptions import PayloadError
from h.tasks import shareflow
from h.util.datetime import timestamp_ms_to_utc

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.trackings",
    request_method="GET",
    permission=Permission.Annotation.CREATE,
    link_name="tracking.read",
    description="Get the user viewing shareflow and scrollTop",
)
def get_trackings(request):
    track = request.session.peek_flash("tracking")
    if track and track[0]:
        return track[0]
    else:
        return { 'id': None, 'scrollToId' : None, }


@api_config(
    versions=["v1", "v2"],
    route_name="api.trackings",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="tracking.update",
    description="Update the user viewing shareflow and scrollTop",
)
def update_trackings(request):
    data = request.json_body

    request.session.pop_flash("tracking")
    request.session.flash(data, "tracking")
    return None


@api_config(
    versions=["v1", "v2"],
    route_name="api.recordings",
    request_method="GET",
    link_name="recordings.read",
    permission=Permission.Annotation.CREATE,
    description="Fetch the user's groups",
)
def recordings(request):
    """Retrieve the groups for this request's user."""
    user = request.user

    service = request.find_service(name="shareflow")
    all = service.get_shareflow_metadata_list_by_user(
        user = user,
        shared = True
    )
    return [
        service.present_shareflow_meta_for_user(shareflow_metadata, user)
        for shareflow_metadata in all
    ]


@api_config(
    versions=["v1", "v2"],
    route_name="api.recordings",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="recording.create",
    description="Create an recording",
)
def create(request):
    """Create an record from the POST payload."""
    payload = _validate(request)
    user = request.user
    userid = request.authenticated_userid
    should_generate = payload.pop("generate", False)

    # TODO remove
    redis_data = create_redis_validate(payload, userid)
    record_item_service = request.find_service(name="record_item")
    record_item = record_item_service.init_user_event_record(redis_data)

    startstamp = redis_data['startstamp']
    session_id = redis_data['session_id']
    task_name = redis_data['task_name']
    request.session.flash(session_id, "recordingSessionId")
    request.session.flash(task_name, "recordingTaskName")

    service = request.find_service(name="shareflow")
    if should_generate:
        shareflow_metadata = service.create_shareflow_metadata_from_record(
            record_item,
            userid,
            timestamp_ms_to_utc(startstamp)
        )
        return service.present_shareflow_meta_for_user(shareflow_metadata, user)
    else:
        return {"id": record_item.pk, "taskName": record_item.task_name}


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="GET",
    # permission=Permission.Annotation.READ,
    link_name="recording.read",
    description="Fetch an recording",
)
def read(context: UserEventRecordContext, request):
    user = request.user
    shareflow_metadata = context.shareflow_metadata
    service = request.find_service(name="shareflow")

    return service.present_shareflow_meta_for_user(shareflow_metadata, user)


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method=("PATCH", "PUT"),
    # permission=Permission.Annotation.UPDATE,
    link_name="recording.update",
    description="Update an recording",
)
def update(context: UserEventRecordContext, request):
    """Update the specified annotation with data from the PATCH payload."""
    metadata = context.shareflow_metadata
    user = request.user
    userid = request.authenticated_userid

    if not user:
        raise HTTPBadRequest()
    command = _json_payload(request)

    publish = False

    service = request.find_service(name="shareflow")
    group_service = request.find_service(name="group")

    if 'endstamp' in command:
        request.session.pop_flash("recordingSessionId")
        request.session.pop_flash("recordingTaskName")
        endstamp = command.pop("endstamp", None)
        generate = command.pop("generate", False)
        if endstamp and isinstance(endstamp, int):
            metadata.endstamp = timestamp_ms_to_utc(endstamp)
            # generate shareflow
            if generate:
                shareflow.generate_shareflows.delay(metadata.session_id)
                publish = True
        else:
            raise PayloadError()
    elif 'regenerate' in command:
        service.regenerate_shareflows(metadata)
    elif 'group' in command:
        action = command.get('action')
        group = group_service.fetch_by_pubid(command.get('group'))
        if action == 'add' and metadata and group:
            service.add_group_to_shareflow_metadata(metadata, group)
        elif action == 'remove' and metadata and group:
            service.remove_group_to_shareflow_metadata(metadata, group)

        request.realtime.publish_tad({
            "messageType": "ShareShareFlow",
            "shareflowMeta": {
                "session_id": metadata.session_id,
                "task_name": metadata.task_name,
                "creator": userid
            },
            "status": "share" if action == 'add' else "unshare",
            "userid": userid,
            "groupid": group.pubid
        })

        publish = True
    elif 'score' in command:
        score = command.pop('score')
        service.add_user_shareflow_metadata(metadata, user, score)
    elif 'shared' in command and isinstance(command['shared'], bool):
        metadata.shared = command.pop('shared')
    elif 'name' in command or 'description' in command:
        if 'name' in command:
            metadata.task_name = command.pop('name')
        if 'description' in command:
            metadata.description = command.pop('description', '')
        publish = True
    elif 'extra' in command:
        metadata.extra = command.pop('extra')
        publish = True
    elif 'pin' in command:
        request.realtime.publish_tad({
            "messageType": "PinShareflow",
            "shareflowMeta": {
                "session_id": metadata.session_id,
                "task_name": metadata.task_name,
            },
            "status": "pin" if command.get("pin") else "unpin",
            "userid": userid
        })
    elif 'request_segmentation' in command:
        all = service.get_shareflows(metadata)
        steps = [
            service.present_shareflow_for_user(shareflow)
            for shareflow in all
        ]
        external_url = request.registry.settings.get("external_url")
        update = service.present_shareflow_meta_for_user(metadata, user)
        extra = update["extra"]
        if not external_url:
            params = {
                'content': steps
            }
            try:
                rpc_svc = request.find_service(name="rpc")
                response = rpc_svc.segmentation(steps)
                extra = {'sections': response.get('sections')}
            except Exception as e:
                raise HTTPBadRequest("RPC LLM Error")
        else:
            # post
            data = {
                "method": "request_segmentation",
                "shareflow_meta": update,
                "steps": steps,
            }
            try:
                resp = requests.post(external_url, json=data, timeout=20)
                resp.raise_for_status()
                result = resp.json()
                extra = result['extra']
            except requests.exceptions.Timeout:
                raise HTTPBadRequest("Request timed out")
            except requests.exceptions.RequestException as e:
                raise HTTPBadRequest("RequestException")
        update["extra"] = extra
        return update

    elif 'request_summary' in command:
        all = service.get_shareflows(metadata)
        steps = [
            service.present_shareflow_for_user(shareflow)
            for shareflow in all
        ]
        url = command.pop("url", '')
        external_url = request.registry.settings.get("external_url")
        if not external_url:
            # rpc
            try:
                rpc_svc = request.find_service(name="rpc")
                response = rpc_svc.summary(metadata.task_name, url, steps)
                update = service.present_shareflow_meta_for_user(metadata, user)
                update['description'] = response.get('summary')
                return update
            except Exception as e:
                pass
        else:
            # post
            meta_dict = service.present_shareflow_meta_for_user(metadata, user)
            data = {
                "method": "request_summary",
                "title":  metadata.task_name,
                "url": url,
                "shareflow_meta": meta_dict,
                "steps": steps,
            }
            try:
                resp = requests.post(external_url, json=data, timeout=20)
                resp.raise_for_status()
                result = resp.json()
                meta_dict['description'] = result['description']
                return meta_dict
            except requests.exceptions.Timeout:
                raise HTTPBadRequest("Request timed out")
            except requests.exceptions.RequestException as e:
                raise HTTPBadRequest("RequestException")

    update = service.present_shareflow_meta_for_user(metadata, user)
    if publish:
        _publish_shareflow_metadata_event(request, update)
    return update


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="DELETE",
    # permission=Permission.Annotation.DELETE,
    link_name="recording.delete",
    description="Delete an recording",
)
def delete(context, request):
    shareflow_metadata = context.shareflow_metadata
    service = request.find_service(name="shareflow")
    succ = service.delete_shareflow_metadata(shareflow_metadata)
    # TODO
    return {"id": shareflow_metadata.session_id, "deleted": succ}


def _json_payload(request):
    """
    Return a parsed JSON payload for the request.

    :raises PayloadError: if the body has no valid JSON body
    """
    try:
        return request.json_body
    except ValueError as err:
        raise PayloadError() from err

def _validate(request):
    payload = _json_payload(request)

    required_fields = [
        "startstamp", "sessionId", "taskName", "backdate", "description"
    ]
    missing_fields = [
        field for field in required_fields if field not in payload
    ]
    if missing_fields:
        raise PayloadError()
    return payload

def create_redis_validate(data, userid):
    new_appstruct = {}

    new_appstruct["userid"] = userid
    new_appstruct["startstamp"] = data["startstamp"]
    new_appstruct["endstamp"] = -1
    new_appstruct["session_id"] = data["sessionId"]
    new_appstruct["task_name"] = data["taskName"]
    new_appstruct["description"] = data["description"]
    new_appstruct["target_uri"] = ''
    new_appstruct["backdate"] = data["backdate"]
    new_appstruct["completed"] = 0
    new_appstruct["groupid"] = ''
    new_appstruct["shared"] = 0

    return new_appstruct

def _publish_shareflow_metadata_event(request, shareflow_metadata):
    """Publish an event to the shareflow queue for this shareflow action."""
    event = ShareflowMetadataEvent(
        request,
        shareflow_metadata,
    )
    request.notify_after_commit(event)
