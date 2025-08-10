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

extra_schema = {
    "type": "object",
    "oneOf": [
        # Case 1: exactly empty object {}
        {"maxProperties": 0},

        # Case 2: has sections with the required structure
        {
            "type": "object",
            "required": ["sections"],
            "properties": {
                "sections": {
                    "type": "array",
                    "minItems": 0,
                    "items": {
                        "type": "object",
                        "required": ["title", "description", "steps_id"],
                        "properties": {
                            "title": {"type": "string", "minLength": 1},
                            "description": {"type": "string", "minLength": 1},
                            "steps_id": {
                                "type": "array",
                                "minItems": 1,
                                "items": {"type": "string", "minLength": 1}
                            }
                        },
                        "additionalProperties": True
                    }
                }
            },
            "additionalProperties": True
        }
    ]
}

request_segmentation_schema = {
    "type": "object",
    "required": ["method", "shareflow_meta", "steps"],
    "properties": {
        "method": {
            "type": "string",
            "enum": ["request_summary", "request_segmentation"]
        },
        "shareflow_meta": {
            "type": "object",
            "required": ["extra"],
            "properties": {
                "extra": extra_schema
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
    "additionalProperties": True,
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
      - method == "request_segmentation"
        Request JSON: {
            "method": string,
            "shareflow_meta": object,
            "steps": List[object],
        }
        Returns JSON: shareflow_meta
        rpc:
            Request: {"content": List[step]}
            Return: {"success": bool, "sections": List[extra]}
    """
    try:
        data = request.json_body
    except Exception:
        raise HTTPBadRequest("Request JSON Error")

    method = data.get('method')
    if method == 'request_summary':
        try:
            validate(instance=data, schema=request_summary_schema)
        except ValidationError as e:
            raise HTTPBadRequest("Request Schema Error")

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
            raise HTTPBadRequest("Request RPC LLM Error")

    elif method == 'request_segmentation':
        try:
            validate(instance=data, schema=request_segmentation_schema)
        except ValidationError as e:
            raise HTTPBadRequest("Request Schema Error")

        shareflow_meta = data.get('shareflow_meta')
        params = {
            'content': data.get('steps')
        }
        try:
            response = request.rpc.call("segmentation", params)
            extra = {'sections': response.get('sections')}
            shareflow_meta['extra'] = extra
            return shareflow_meta
        except Exception as e:
            raise HTTPBadRequest("Request RPC LLM Error")

    elif method == 'request_query':
        querying = data.get('q')
        if querying is None or querying.strip() == "":
            return {
                'status': "500",
                'query': 'missing query or invaild query',
                'context': []
            }

        params = {'q': querying}
        try:
            response = request.rpc.call("query", params)
            return response
        except Exception as e:
            return {
                'status' : str(e),
                'query' : querying,
                'context' : []
            }
