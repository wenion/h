from pyramid.events import subscriber
from urllib.parse import unquote, urlparse, parse_qs

from h.accounts.events import LoginEvent, LogoutEvent, AuthLoginEvent


@subscriber(LoginEvent)
def save_login_event(event):
    event.request.find_service(name="trace").create_server_event(
        event.user.userid, "login", "login", "landing page login"
    )


@subscriber(LogoutEvent)
def save_logout_event(event):
    event.request.find_service(name="trace").create_server_event(
        event.request.authenticated_userid, "logout", "logout", "landing page logout"
    )


@subscriber(AuthLoginEvent)
def save_auth_login_event(event):
    pass
    # url = event.request.url
    # print('url', url)
    # parsed_url = urlparse(url)
    # query_params = parse_qs(parsed_url.query)
    # origin_values = query_params.get('origin', [])
    # text_content = "unauthorize login"
    # if origin_values and origin_values[0]:
    #     decoded_url = unquote(origin_values[0])
    #     if "chrome-extensions" in decoded_url:
    #         text_content = "browser extension login"
    #     else:
    #         text_content = "query login"
    #     create_user_event("sever-record", "LOGIN", text_content, decoded_url, event.request.authenticated_userid)
    # else:
    #     create_user_event("sever-record", "LOGIN", text_content, url, event.request.authenticated_userid)
