import html2text
import logging
import requests
from urllib.parse import urljoin

from h.models_redis import is_task_page

log = logging.getLogger(__name__)


def handle_web_page(message, registry=None):
    if not message.socket.identity:
        message.reply(
            {
                "type": "whoyouare",
                "userid": message.socket.identity.user.userid if message.socket.identity else None,
                "error": {"type": "invalid_connection", "description": '"userid" is missing'},
            },
            ok=False,
        )
        return
    data = message.payload
    page_url = data["url"]
    try:
        parser = html2text.HTML2Text()
        parser.ignore_links = True
        plain_text = parser.handle(data["textContent"])
    except Exception as e:
        log.error("html2text", e)
        plain_text = ''

    url = urljoin(registry.settings.get("query_url"), "knowledge")

    data = {
        'userid': message.socket.identity.user.userid,
        'content': plain_text,
    }

    if is_task_page(page_url):
        return

    response = requests.post(url, data=data)
    if response.status_code == 200:
        try:
            json_data = response.json()
            message.socket.send_json(
                {
                    "type": "knowledge-push",
                    "payload": json_data
                },
            )
        except ValueError:
            message.socket.send_json(
                {
                    "type": "knowledge-push",
                    "payload": None,
                    "error": response.text
                },
            )
    else:
        message.socket.send_json(
            {
                "type": "knowledge-push",
                "payload": None,
                "error": f'Error {response.status_code}: {response.text}'
            }
        )
