import json
from pyramid import i18n
from pyramid.httpexceptions import HTTPBadRequest, HTTPUnauthorized
from jsonschema import validate, ValidationError

from h.views.api.config import api_config

_ = i18n.TranslationStringFactory(__package__)


request_summary_schema = {
    "type": "object",
    "required": ["method", "title", "url", "shareflow_meta", "steps"],
    "properties": {
        "method": {
            "type": "string",
            "enum": ["request_summary", "request_segmentation"]
        },
        "title":  {"type": "string", "minLength": 1, "maxLength": 512},
        "url":    {"type": "string", "format": "uri"},
        "shareflow_meta": {
            "type": "object",
            "required": ["description"],
            "properties": {
                "description": {
                    "type": "string",
                    "minLength": 0
                }
            },
            "additionalProperties": True
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "description", "url"],
                "properties": {
                    "id": {"type": "string"},
                    "index": {"type": "integer", "minimum": 0},
                    "title": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "type": {"type": "string"},
                    "url": {"type": "string"},
                    "tagName": {"type": "string"},
                    "timestamp": {"type": "number"},
                },
                "additionalProperties": True
            }
        }
    },
    "additionalProperties": False,
}

@api_config(
    versions=["v1", "v2"],
    route_name="api.external",
    request_method="POST",
    link_name="external.create",
    description="Access resources",
)
def external(request):
    """
    POST /api/external
    Accepts JSON payloads for two operations:
      - method == "request_summary": generate a summary from steps, returns metadata with description
        Request JSON: {
            "method": string,
            "title": string,
            "url": string,
            "shareflow_meta": object,
            "steps": List[object],
        }
        Returns JSON: shareflow_meta
        rpc:
            Request: {"title": string, "url": string, "content": List[step]}
            Return: {"success": bool, "summary": string, "title": string, "url": string}
    """
    try:
        data = request.json_body
    except Exception:
        raise HTTPBadRequest()

    method = data.get('method')
    if method == 'request_summary':
        try:
            validate(instance=data, schema=request_summary_schema)
        except ValidationError as e:
            raise HTTPBadRequest()

        shareflow_meta = data.get('shareflow_meta')
        data = {
            'title': data.get('title'),
            'url': data.get('url'),
            'content': data.get('steps')
        }
        try:
            response = request.rpc.call("summary", data)

            shareflow_meta['description'] = response.get('summary')
            return shareflow_meta
        except Exception as e:
            raise HTTPBadRequest()

    elif method == 'request_segmentation':
        pass
