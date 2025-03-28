import json
import logging
from functools import wraps
from urllib.parse import parse_qs, urlparse

from oauthlib.oauth2 import OAuth2Error
from pyramid.httpexceptions import HTTPFound, exception_response
from pyramid.view import view_config, view_defaults

from h import models
from h.services.oauth import DEFAULT_SCOPES
from h.util.datetime import utc_iso8601
from h.views.api.config import api_config
from h.views.api.exceptions import OAuthAuthorizeError, OAuthTokenError

log = logging.getLogger(__name__)


def handles_oauth_errors(wrapped):
    """
    Catch oauthlib errors and raise an appropriate exception.

    This prevents unhandled errors from crashing the app.
    """

    @wraps(wrapped)
    def inner(*args, **kwargs):
        try:
            return wrapped(*args, **kwargs)

        except OAuth2Error as err:
            raise OAuthAuthorizeError(err.description) from err

    return inner


@view_defaults(route_name="oauth_authorize")
class OAuthAuthorizeController:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.user_svc = self.request.find_service(name="user")
        self.oauth = self.request.find_service(name="oauth_provider")

    @view_config(
        request_method="GET", renderer="h:templates/oauth/authorize.html.jinja2"
    )
    def get(self):
        """
        Validate the OAuth authorization request.

        If the authorization request is valid and the client is untrusted,
        this will render an authorization page allowing the user to
        accept or decline the request.

        If the authorization request is valid and the client is trusted,
        this will skip the users' confirmation and create an authorization
        code and deliver it to the client application.
        """
        return self._authorize()

    @view_config(
        request_method="GET",
        request_param="response_mode=web_message",
        renderer="h:templates/oauth/authorize.html.jinja2",
    )
    def get_web_message(self):
        """
        Validate the OAuth authorization request for response mode ``web_response``.

        This is doing the same as ``get``, but it will deliver the
        authorization code (if the client is trusted) as a ``web_response``.
        More information about ``web_response`` is in draft-sakimura-oauth_.

        .. _draft-sakimura-oauth: https://tools.ietf.org/html/draft-sakimura-oauth-wmrm-00
        """
        response = self._authorize()

        if isinstance(response, HTTPFound):
            self.request.override_renderer = (
                "h:templates/oauth/authorize_web_message.html.jinja2"
            )
            return self._render_web_message_response(response.location)

        return response

    @view_config(
        request_method="POST",
        is_authenticated=True,
        renderer="json",
    )
    def post(self):
        """
        Create an OAuth authorization code.

        This validates the request and creates an OAuth authorization code
        for the authenticated user, it then returns this to the client.
        """
        return self._authorized_response()

    @view_config(
        request_method="POST",
        request_param="response_mode=web_message",
        is_authenticated=True,
        renderer="h:templates/oauth/authorize_web_message.html.jinja2",
    )
    def post_web_message(self):
        """
        Create an OAuth authorization code.

        This is doing the same as ``post``, but it will deliver the
        authorization code as a ``web_response``.
        More information about ``web_response`` is in draft-sakimura-oauth_.

        .. _draft-sakimura-oauth: https://tools.ietf.org/html/draft-sakimura-oauth-wmrm-00
        """
        found = self._authorized_response()
        return self._render_web_message_response(found.location)

    def _authorize(self):
        try:
            _, credentials = self.oauth.validate_authorization_request(self.request.url)
        except OAuth2Error as err:
            raise OAuthAuthorizeError(
                err.description or f"Error: {self.context.error}"
            ) from err

        if self.request.authenticated_userid is None:
            raise HTTPFound(
                self.request.route_url(
                    "login", _query={"next": self.request.url, "for_oauth": True}
                )
            )

        client_id = credentials.get("client_id")
        client = self.request.db.query(models.AuthClient).get(client_id)

        # If the client is "trusted" -- which means its code is
        # owned/controlled by us -- then we don't ask the user to explicitly
        # authorize it. It is assumed to be authorized to act on behalf of the
        # logged-in user.
        if client.trusted:
            return self._authorized_response()

        state = credentials.get("state")
        user = self.user_svc.fetch(self.request.authenticated_userid)
        response_mode = credentials.get("request").response_mode

        return {
            "username": user.username,
            "client_name": client.name,
            "client_id": client.id,
            "response_mode": response_mode,
            "response_type": client.response_type.value,
            "state": state,
        }

    @handles_oauth_errors
    def _authorized_response(self):
        # We don't support scopes at the moment, but oauthlib does need a scope,
        # so we're explicitly overwriting whatever the client provides.
        scopes = DEFAULT_SCOPES
        user = self.user_svc.fetch(self.request.authenticated_userid)
        credentials = {"user": user}

        headers, _, _ = self.oauth.create_authorization_response(
            self.request.url, scopes=scopes, credentials=credentials
        )

        # obtain browser extension origin to pass auth
        header_list = headers["Location"].split('?')
        header_list[0] = self.request.params.getone('origin') + '?'
        headers["Location"] = ''.join(header_list)

        try:
            return HTTPFound(location=headers["Location"])
        except KeyError as err:
            client_id = self.request.params.get("client_id")
            raise RuntimeError(
                f'created authorisation code for client "{client_id}" but got no redirect location'
            ) from err

    @classmethod
    def _render_web_message_response(cls, redirect_uri):
        location = urlparse(redirect_uri)
        params = parse_qs(location.query)
        origin = "{url.scheme}://{url.netloc}".format(url=location)

        state = None
        states = params.get("state", [])
        if states:
            state = states[0]

        return {"code": params.get("code", [])[0], "origin": origin, "state": state}


class OAuthAccessTokenController:
    def __init__(self, request):
        self.request = request

        self.oauth = self.request.find_service(name="oauth_provider")

    @api_config(versions=["v1", "v2"], route_name="token", request_method="POST")
    @handles_oauth_errors
    def post(self):
        _, body, status = self.oauth.create_token_response(
            self.request.url,
            self.request.method,
            self.request.POST,
            self.request.headers,
        )

        if status == 200:
            return json.loads(body)

        raise exception_response(status, detail=body)


class OAuthRevocationController:
    def __init__(self, request):
        self.request = request

        self.oauth = self.request.find_service(name="oauth_provider")

    @api_config(versions=["v1", "v2"], route_name="oauth_revoke", request_method="POST")
    @handles_oauth_errors
    def post(self):
        _, body, status = self.oauth.create_revocation_response(
            self.request.url,
            self.request.method,
            self.request.POST,
            self.request.headers,
        )
        if status == 200:
            return {}

        raise exception_response(status, detail=body)


@api_config(versions=["v1", "v2"], route_name="api.debug_token", request_method="GET")
def debug_token(request):
    svc = request.find_service(name="auth_token")

    bearer_token = svc.get_bearer_token(request)
    if not bearer_token:
        raise OAuthTokenError(
            "Bearer token is missing in Authorization HTTP header", "missing_token"
        )

    if not svc.validate(bearer_token):
        raise OAuthTokenError(
            "Bearer token does not exist or is expired", "missing_token"
        )

    token = svc.fetch(bearer_token)
    return _present_debug_token(token)


@api_config(
    versions=["v1", "v2"],
    context=OAuthTokenError,
    # This is a handler called only if a request fails, so the CORS
    # preflight request will have been handled by the original view.
    enable_preflight=False,
)
def api_token_error(context, request):
    """Handle an expected/deliberately thrown API exception."""
    request.response.status_code = context.status_code
    resp = {"error": context.type}
    if context.args[0]:
        resp["error_description"] = str(context)
    return resp


def _present_debug_token(token):
    data = {
        "userid": token.userid,
        "expires_at": utc_iso8601(token.expires),
        "issued_at": utc_iso8601(token.created),
        "expired": token.expired,
    }

    if token.authclient:
        data["client"] = {"id": token.authclient.id, "name": token.authclient.name}

    return data
