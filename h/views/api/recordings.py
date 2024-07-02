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
from urllib.parse import urljoin
import requests
from pyramid import i18n

from h.models_redis import start_user_event_record, finish_user_event_record
from h.models_redis import batch_user_event_record, update_user_event_record, delete_user_event_record
from h.views.api.user_manipultations import batch_steps
from h.views.api.data_comics_process import data_commics_process
from h.security import Permission
from h.views.api.config import api_config
from h.views.api.data_comics import create_images_DC

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.batch",
    link_name="batch",
    description="batch",
)
def batch(request):
    # TODO if authenticated userid is none
    page_url = request.params.get('target_uri')
    index_list = batch_user_event_record(request.authenticated_userid)
    results = []
    for record in index_list:
        results.append({
            "taskName": record.task_name,
            'sessionId': record.session_id,
            "timestamp": record.startstamp,
            "steps": None,
            "task_name": record.task_name,
            "session_id": record.session_id,
            "userid": record.userid,
            "groupid": record.groupid,
            "shared": record.shared
            })
    return results


@api_config(
    versions=["v1", "v2"],
    route_name="api.recordings",
    request_method="POST",
    permission=Permission.Annotation.CREATE,
    link_name="recording.create",
    description="Create an recording",
)
def create(request):
    """Create an annotation from the POST payload."""
    data = request.json_body
    result = start_user_event_record(
        data['startstamp'],
        data['session_id'],
        data['task_name'],
        data['description'],
        data['target_uri'],
        data['start'],
        request.authenticated_userid,
        data['groupid'],
        )
    return result.dict()


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="GET",
    # permission=Permission.Annotation.READ,
    link_name="recording.read",
    description="Fetch an recording",
)
def read(context, request):
    record = context.user_event_record
    results = batch_steps([record, ])
    if len(results):
        return results[0]
    else:
        return [{
            "taskName": record.task_name,
            'sessionId': record.session_id,
            "timestamp": record.startstamp,
            "steps": None,
            "task_name": record.task_name,
            "session_id": record.session_id,
            "userid": record.userid,
            "groupid": record.groupid,
            "shared": record.shared
            },]


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method=("PATCH", "PUT"),
    # permission=Permission.Annotation.UPDATE,
    link_name="recording.update",
    description="Update an recording",
)
def update(context, request):
    """Update the specified annotation with data from the PATCH payload."""
    data = request.json_body
    action = data["action"]
    if action == "finish":
        print("FINISHHHHHHH:")
        session = finish_user_event_record(context.pk, data["endstamp"])
        result = batch_steps([session,])
        resultDC=data_commics_process(result)
        create_images_DC(resultDC)
        # Steve: create process model after Shareflow recording completes
        try:
            tad_url = urljoin(request.registry.settings.get("tad_url"), "create_process_model")
            pm_data = {"user_id": context.user_event_record.userid,
                       "shareflow_name": context.user_event_record.task_name,
                       "session_id": context.user_event_record.session_id,
                       "group_id": context.user_event_record.groupid}
            headers = {"Content-Type": "application/json"}
            pm_creation_response = requests.post(tad_url, json=pm_data, headers=headers)
            if not pm_creation_response["created"]:
                print("Unable to create process model due to", pm_creation_response["message"])
        except Exception as e:
            print("Process model not created due to error:", e)
            pass
        return result[0] if len(result) > 0 else session.dict()
    elif action == "share":
        user_event_record = context.user_event_record.dict()
        user_event_record['shared'] = 1 if data["shared"] else 0
        result = update_user_event_record(user_event_record['pk'], user_event_record, None).dict()
        return result
    elif action == "edit":
        pass


@api_config(
    versions=["v1", "v2"],
    route_name="api.recording",
    request_method="DELETE",
    # permission=Permission.Annotation.DELETE,
    link_name="recording.delete",
    description="Delete an recording",
)
def delete(context, request):
    # Steve: delete process model when Shareflow gets deleted
    try:
        tad_url = urljoin(request.registry.settings.get("tad_url"), "delete_process_model")
        pm_data = {"user_id": context.user_event_record.userid,
                  "shareflow_name": context.user_event_record.task_name,
                  "session_id": context.user_event_record.session_id}
        headers = {"Content-Type": "application/json"}
        pm_deletion_response = requests.post(tad_url, json=pm_data, headers=headers)
        if not pm_deletion_response["created"]:
            print("Unable to delete process model due to", pm_deletion_response["message"])
    except Exception as e:
        print("Process model not deleted due to error:", e)
        pass

    return context.session_id if delete_user_event_record(context.pk) else -1


