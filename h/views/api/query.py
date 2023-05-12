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

from h.views.api.config import api_config

_ = i18n.TranslationStringFactory(__package__)


@api_config(
    versions=["v1", "v2"],
    route_name="api.query",
    link_name="query",
    description="Querying",
)
def query(request):
    query = request.GET.get('q')
    url = request.registry.settings.get("query_url")
    params = {
        'q': query
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        json_data = response.json()
        # count = 0
        # for topic in json_data['context']:
        #     print('topic id ', count)
        #     rcount = 0
        #     for result in topic:
        #         print('result id ', rcount, result)
        #         rcount += 1
        #     count += 1

        return json_data
    else:
        print('Request failed with status code:', response.status_code)
        return {
            'status' : "proxy reverse can't get the response, status code: " + str(response.status_code),
            'query' : query,
            'context' : []
        }
