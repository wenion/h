from pyramid.events import subscriber
from urllib.parse import unquote, urlparse, parse_qs

from h.accounts.events import LoginEvent, LogoutEvent, AuthLoginEvent
from h.models_redis import UserEvent, create_user_event, save_in_redis


@subscriber(LoginEvent)
def save_login_event(event):
    login_event = create_user_event("sever-record", "LOGIN", "landing login", event.request.url, event.user.userid)
    save_in_redis(login_event)


@subscriber(LogoutEvent)
def save_logout_event(event):
    logout_event = create_user_event("sever-record", "LOGOUT", "landing logout", event.request.url, event.request.authenticated_userid)
    save_in_redis(logout_event)


@subscriber(AuthLoginEvent)
def save_auth_login_event(event):
    url = event.request.url
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    origin_values = query_params.get('origin', [])
    text_content = "unauthorize login"
    if origin_values and origin_values[0]:
        decoded_url = unquote(origin_values[0])
        if "chrome-extensions" in decoded_url:
            text_content = "browser extension login"
        else:
            text_content = "query login"
        auth_login_event = create_user_event("sever-record", "LOGIN", text_content, decoded_url, event.request.authenticated_userid)
        save_in_redis(auth_login_event)
    else:
        auth_login_event = create_user_event("sever-record", "LOGIN", text_content, url, event.request.authenticated_userid)
        save_in_redis(auth_login_event)
